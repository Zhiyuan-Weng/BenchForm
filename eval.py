from time import time
from string import ascii_uppercase
import traceback
import re
import json
import glob
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import time
from tqdm import tqdm
from collections import defaultdict
import traceback
import ollama
import openai
import argparse
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, Color
from utils import Config, SEP, generate_gpt, generate_gpt_empowered, generate_ollama, generate_ollama_empowered, generate_glm, generate_glm_empowered
from format_data_bbh import format_example_pairs


parser = argparse.ArgumentParser()
parser.add_argument('--previous_discussions_rounds', default=5, type=int, help='total rounds = previous_dicussions_rounds (<=5) + current round (1)')
parser.add_argument('--majority_num', default=6, type=int, help='>=3 and <=6')
parser.add_argument('--model', type=str, required=True)
parser.add_argument('--save_path', type=str, required=True)

parser.add_argument('--dataset', default='bbh', type=str)
parser.add_argument('--mode', default='default', type=str, choices=['default', 'empowered'])

args = parser.parse_args()

ans_map = {k: v for k,v in zip(ascii_uppercase, range(26))}

# Set to true to run on a small subset of the data
testing = False
    
def extract_answer(model_answer):
    try:
        
        tmp=model_answer.split('is: "(')
        if len(tmp) == 1:
            tmp = model_answer.split('is: (')
        if len(tmp) == 1:
            tmp = model_answer.split('is (')
        assert len(tmp) > 1, "model didn't output trigger"
        assert tmp[-1][1] == ')', "didnt output letter for choice"
        pred = tmp[-1][0]
        return pred
    except Exception as e:
        return traceback.format_exc()

def save_to_xlsx(data, xlsx_path):
    
    flattened_data = {}
    for key, value in data.items():
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                flattened_data[nested_key] = nested_value
        else:
            flattened_data[key] = value
    
    df = pd.DataFrame([flattened_data])
    
    delete_key_lst = ['batch', 'fname']
    for delete_key in delete_key_lst:
        if delete_key in df.columns:
            df = df.drop([delete_key], axis=1)
    
    
    if 'inputs' in df.columns and isinstance(df['inputs'].values[0], list):
        df = df.reindex(df.index.repeat(len(df['inputs'].values[0])))
        
        list_columns = ['inputs', 'y_pred', 'y_true', 'outputs']
        for col in list_columns:
            if col in df.columns and isinstance(df[col].values[0], list):
                for i in range(len(df[col].values[0])):
                    df.iloc[i, df.columns.get_loc(col)] = df.iloc[i, df.columns.get_loc(col)][i]
    
    if 'y_pred' in df.columns and 'y_true' in df.columns:
        is_correct = df['y_pred'] == df['y_true']
        y_true_index = df.columns.get_loc('y_true')
        df.insert(y_true_index + 1, 'is_correct', is_correct)
    
    df.to_excel(xlsx_path, index=False)
    
    wb = load_workbook(xlsx_path)
    ws = wb.active
    
    for column_cells in ws.columns:
        key_length = len(str(column_cells[0].value))
        value_length = max([len(str(cell.value)) for cell in column_cells[1:] if cell.value is not None], default=0)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(key_length*2, value_length+5), 60)
    
    wb.save(xlsx_path)
    return df

def get_results_on_instance_i(i, format_inps, data, c, failed_idx):
    kv_outputs_list = []

    inp = format_inps[i]
    y_true = data[i]['multiple_choice_scores'].index(1)

    row = data[i]

    if args.mode == 'default':
        if c.model in ['gpt-3.5-turbo', 'gpt-4', 'gpt-4o']:
            out = generate_gpt(inp, model=c.model, temperature=.7)
        elif c.model in ['GLM-4-Plus']:
            out = generate_glm(inp, model=c.model)
        else:
            out = generate_ollama(inp, model=c.model)
    elif args.mode == 'empowered':
        if c.model in ['gpt-3.5-turbo', 'gpt-4', 'gpt-4o']:
            out = generate_gpt_empowered(inp, model=c.model, temperature=.7)
        elif c.model in ['GLM-4-Plus']:
            out = generate_glm_empowered(inp, model=c.model)
        else:
            out = generate_ollama_empowered(inp, model=c.model)
    pred = extract_answer(out)

    # Catch failures
    if pred not in ascii_uppercase:
        if i not in failed_idx:
            failed_idx.append(i)

    kv_outputs = {
        'inputs': inp,
        'outputs': out,
        'y_pred': int(ans_map.get(pred, -1)),
        'y_true': y_true,
    }
    
    kv_outputs_list.append(kv_outputs)

    return kv_outputs_list

def main():
    # use this to retry examples that previously failed
    # List paths to the json files for the results you want to retry
    configs_to_resolve = [] 

    if configs_to_resolve:
        print('CONFIGS TO RESOLVE')
        configs = []
        for con in configs_to_resolve:
            newcon = Config('')
            with open(con,'r') as f:
                newcon.__dict__ = json.load(f)["config"]
            configs.append(newcon)
            
            assert str(newcon)+'.json' in os.listdir('samples')
    else:

        configs = []
        
        ### Note: multi_rounds==True and protocol=='raw' are not used in the paper
        ### 'Wrong Guidance' is represented by multi_rounds==False and protocol=='trust' for convenience
        ### 'Correct Guidance' is represented by multi_rounds==False and protocol=='doubt' for convenience
        
        for multi_rounds in [False, True]:
            for model in [args.model]:
                for task in [
                    'sports_understanding',
                    'snarks',
                    'disambiguation_qa',
                    'movie_recommendation',
                    'causal_judgment',
                    'date_understanding',
                    'tracking_shuffled_objects_three_objects',
                    'temporal_sequences',
                    'ruin_names',
                    'web_of_lies',
                    'navigate',
                    'logical_deduction_five_objects',
                    'hyperbaton',
                ]:
                    if multi_rounds == False:
                        configs.append(
                            Config(task, 
                                    protocol='raw',
                                    multi_rounds = multi_rounds,
                                    previous_discussions_rounds = args.previous_discussions_rounds,
                                    majority_num = args.majority_num,
                                    model=model,
                                    batch=5,
                                    mode=args.mode))
                    configs.append(
                        Config(task, 
                                protocol='trust',
                                multi_rounds = multi_rounds,
                                previous_discussions_rounds = args.previous_discussions_rounds,
                                majority_num = args.majority_num,
                                model=model,
                                batch=5,
                                mode=args.mode))
                    configs.append(
                        Config(task, 
                                protocol='doubt',
                                multi_rounds = multi_rounds,
                                previous_discussions_rounds = args.previous_discussions_rounds,
                                majority_num = args.majority_num,
                                model=model,
                                batch=5,
                                mode=args.mode))



    for i,c in enumerate(configs):
        for j,c_ in enumerate(configs):
            if i != j:
                assert str(c) != str(c_), (str(c), str(c_))

    first_start = time()

    is_failed_example_loop = False  # keep this as false; rerun failed examples on 2nd loop! set to true at bottom of block 

    for t in range(2):  
        if configs_to_resolve and not is_failed_example_loop: # skip first loop if doing post failure filling
            print('SKIPPING FIRST LOOP, USING CONFIGS IN CONFIGS_TO_RESOLVE')
            is_failed_example_loop = True
            continue
        
        for c in configs:
            
            fname = c.fname if hasattr(c,'fname') else str(c)+'.json'

            print('\n\n\nNew config')
            print(c.__dict__)
            
            try:

                if args.dataset == 'bbh':
                    with open(f'data/bbh/{c.task}/val_data.json','r') as f:
                        data = json.load(f)['data']

                if testing:
                    print('TESTING')
                    data=data[:5]

                format_inps = format_example_pairs(data, c)
                
                outputs = defaultdict(lambda: [None for _ in range(len(data))])
                idx_list = range(len(data))

                # Determine which examples to go over
                if is_failed_example_loop:

                    with open(f'{args.save_path}/{fname}','r') as f:
                        results = json.load(f)
                    
                    # Load up `outputs` with the results from the completed examples
                    outputs.update(results['outputs'])

                    idx_list = results['failed_idx'] 
                    print('Going over these examples:', idx_list)
                    
                failed_idx = []
                
                future_instance_outputs = {}
                batch = 1 if not hasattr(c, 'batch') else c.batch
                with ThreadPoolExecutor(max_workers=batch) as executor:
                    for idx in idx_list:
                        future_instance_outputs[executor.submit(get_results_on_instance_i, idx, format_inps, data, c, failed_idx)] = idx 
                    
                    for cnt, instance_outputs in enumerate(tqdm(as_completed(future_instance_outputs), total=len(future_instance_outputs), desc="Processing")):
                        start = time()
                        i = future_instance_outputs[instance_outputs]
                        kv_outputs_list = instance_outputs.result(timeout=500)
                        kv_outputs = kv_outputs_list[0]
                        for key, val in kv_outputs.items():
                            outputs[key][i] = val

                        # Compute metrics and write results
                        if cnt + 1 % 100 == 0 or cnt + 1 == len(idx_list):
                            
                            print('=== PROGRESS: ', cnt + 1, '/', len(idx_list), '===')
                            
                                
                            acc = sum([int(y==z) for y,z in zip(outputs['y_pred'], outputs['y_true']) if y is not None and z is not None])

                            print('Acc:', acc)
                            print('Num failed:', len(failed_idx))

                            os.makedirs(args.save_path, exist_ok=True)
                            
                            # revise the protocol
                            if c.multi_rounds == False and c.protocol == 'trust':
                                c.protocol = 'wrong guidance'
                            elif c.multi_rounds == False and c.protocol == 'doubt':
                                c.protocol = 'correct guidance'
                            
                            with open(f'{args.save_path}/{fname}','w') as f:
                                json.dump({
                                    'config': c.__dict__,
                                    'fname': fname,
                                    'correct_num': acc,
                                    'failed_idx': failed_idx,
                                    'outputs':outputs,
                                }, f)
                            
                            xlsx_path = f'{args.save_path}/{fname[:-5]}.xlsx'
                            save_to_xlsx({
                                    'config': c.__dict__,
                                    'correct_num': acc,
                                    'failed_idx': failed_idx,
                                    'outputs':outputs,
                                }, xlsx_path)

            except KeyboardInterrupt:
                for t in future_instance_outputs:
                    t.cancel()
                break
            except Exception as e:
                traceback.print_exc()
                for t in future_instance_outputs:
                    t.cancel()
        
        is_failed_example_loop = True

    print('Finished in', round(time() - first_start), 'seconds')

if __name__ == '__main__':
    main()