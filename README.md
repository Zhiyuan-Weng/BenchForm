# Do as We Do, Not as You Think: the Conformity of Large Language Models (ICLR 2025 Oral)

![](docs/protocols.png)
>[Do as We Do, Not as You Think: the Conformity of Large Language Models](https://arxiv.org/abs/2501.13381) <br>
>[Zhiyuan Weng](https://scholar.google.com/citations?user=2Lf0vYQAAAAJ), [Guikun Chen](https://scholar.google.com/citations?user=I1TOdpkAAAAJ), [Wenguan Wang](https://sites.google.com/view/wenguanwang)

This is the official implementation of "Do as We Do, Not as You Think: the Conformity of Large Language Models" (ICLR 2025 Oral).

## Abstract

Recent advancements in large language models (LLMs) revolutionize the field of intelligent agents, enabling collaborative multi-agent systems capable of tackling complex problems across various domains. However, the potential of conformity within these systems, analogous to phenomena like conformity bias and groupthink in human group dynamics, remains largely unexplored, raising concerns about their collective problem-solving capabilities and possible ethical implications. This paper presents a comprehensive study on conformity in LLM-driven multi-agent systems, focusing on three aspects: the existence of conformity, the factors influencing conformity, and potential mitigation strategies. In particular, we introduce *BenchForm*, a new conformity-oriented benchmark, featuring reasoning-intensive tasks and five distinct interaction protocols designed to probe LLMs' behavior in collaborative scenarios. Several representative LLMs are evaluated on *BenchForm*, using metrics such as conformity rate and independence rate to quantify conformity's impact. Our analysis delves into factors influencing conformity, including interaction time and majority size, and examines how the subject agent rationalizes its conforming behavior. Furthermore, we explore two strategies to mitigate conformity effects, i.e., developing enhanced personas and implementing a reflection mechanism. Several interesting findings regarding LLMs' conformity are derived from empirical results and case studies. We hope that these insights can pave the way for more robust and ethically-aligned collaborative AI systems. Our benchmark and code are available at *BenchForm*.

## Citation

If you find this work useful in your research, please star our repository and consider citing:

```
@inproceedings{weng2025benchform,
      title={Do as We Do, Not as You Think: the Conformity of Large Language Models}, 
      author={Weng, Zhiyuan and Chen, Guikun and Wang, Wenguan},
      booktitle={ICLR},
      year={2025}
}
```

## Contact

Any comments, please email: zhiyuanweng111@gmail.com.
