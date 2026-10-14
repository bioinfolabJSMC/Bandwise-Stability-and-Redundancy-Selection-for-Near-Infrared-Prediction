# 白首乌近红外光谱 SPXY 分析与完整绘图程序

本包以附件中的84个样本、141个实测光谱变量和对应C21甾苷含量重新计算。输入为 `inputs/baishouwu_spectra.mat`，包含X（84×141）、wv（波长）及y（参考含量）。光谱变量和对应波长成对按升序排列；样本与含量对应关系保持一致。`inputs/manifest.json`记录附件来源校验值和输入校验值。

仅采用SPXY划分：63个校正样本、21个预测样本。使用全部141个原始光谱变量的欧氏距离与含量绝对距离，两者分别除以各自最大值后相加；首先选择距离最远的样本对，再逐次选择与已选集合的最小距离最大的样本，直到校正集达到63个。划分过程确定性执行，随机种子用于后续校正交叉验证与变量选择重复抽样。

## 运行

安装Python 3.12，并启用Python Launcher（py）。解压整个程序目录，双击 `install_dependencies.bat` 安装锁定依赖，再双击 `run_analysis.bat`。也可运行：

```powershell
python -m pip install -r requirements_lock.txt
python run_all.py
```

完整流程依次运行分析、绘图、结果核对、EndNote导出、Word生成，输出到 `results`。重新运行会覆盖本程序产生的结果。源码按自身路径定位文件，可以从其它工作目录调用。Times New Roman必须已安装；找不到该字体时程序明确报错。文稿绑定输入校验值和数值签名，更换数据或模型结果后需同步改写正文再生成Word。

单幅图不添加(a)面板标记，多面板图保留字母编号。

只修改图或文稿时，可分别运行：

```powershell
python plot_figures.py
python verify_results.py
python export_references.py
python build_manuscript.py
```

## 代码

| 文件 | 功能 |
|---|---|
| run_all.py | 完整执行流程 |
| data_io.py | 检查并读取141个光谱变量与响应 |
| analysis.py | SPXY、预处理、PLS、变量选择、消融、逐样本预测与冻结模型 |
| plot_figures.py | 全部7张正文图和4张补充图的绘图代码及图注 |
| verify_results.py | 独立复核SPXY样本成员、PLS预测、模型指标与图像分辨率 |
| export_references.py | 按正文首次引用顺序生成27条EndNote RIS/XML文献记录 |
| build_manuscript.py | 根据Foods模板、最新结果与正文资源生成两份Word |
| math_equations.py | 13个可编辑Word公式及行内数学符号 |
| predict_new.py | 使用冻结模型预测同一波长网格的新样本 |

## 方法设置与解释

| 项目 | 设置 |
|---|---|
| 划分 | SPXY，63校正/21预测；141个原始变量的联合光谱与响应距离 |
| 预处理 | Raw、MSC、SNV、CWT、一阶导数D1、二阶导数D2 |
| MSC | 每个训练折的均值谱为参照，应用到该折验证样本 |
| SNV | 单谱均值中心化和样本标准差归一化 |
| D1/D2 | 141点均匀插值网格，15点Savitzky–Golay、三次多项式、镜像边界，使用实际nm间距 |
| CWT | Mexican hat、scale 10、integration precision 10、两端40点反射边界扩展 |
| PLS | 均值中心化，不autoscale；1–10个LV，受变量与样本维度限制 |
| 模型 | Full、UVE rank、MC-UVE rank、RT、改编C-value、提出的BSRS |
| 变量数候选 | 4、8、16、32、64、71、128；Full使用141 |
| 调优 | 校正集5折；每折重新拟合预处理、变量排序和PLS |
| 重复抽样 | 100次80%不放回抽样，seed 20261006 |
| RT | 199次训练响应置换，有限样本修正概率用于排序 |
| C-value | 2p行随机包含设计、70%包含，3折内部误差，C=pinv(F)e |
| BSRS | log(1+系数可靠性)×符号一致性，5点局部均值，相关冗余权重2 |

UVE与MC-UVE主比较使用明确标注的可靠性排序前缀变体；变量数和LV由校正RMSECV选择。RT是random test，不是Random Frog，不将其排序概率解释为经过多重检验校正的发现。C-value保留原贡献机制，随机包含设计属于明确的改编实现。BSRS的局部均值是相应局部最小二乘问题的解，整体方法采用贪心排序；不声称全局最优或精度保证。

本次校正准则选择D2及BSRS（8变量、3 LV）。其RMSECV为3.457 mg/g，预测RMSEP为2.806 mg/g，R²p为0.876；全谱RMSEP为2.897 mg/g。RT的预测RMSEP为2.746 mg/g，是主模型比较中的最低留出误差。预测结果不用于改选模型。消融比较亦不用于按预测误差重设算法。调优RMSECV是用于选择设置的误差，不能当作无偏泛化误差。

D1、D2和CWT的选择位置位于均匀插值工作网格，不应误当作原始测量位置或直接作为分子振动指认。Figure 6红线是保存的参考与预测值的描述性线性拟合，不用于改变预测模型。

## 文件与新样本

`results/analysis`包括样本分配、SPXY集合统计、预处理和变量方法结果、逐样本预测、所选变量、消融、运行环境、数值核对报告及 `frozen_models.npz`。`results/figures`包括11组PNG/TIFF，均300 dpi、Times New Roman，Word与PNG嵌图一致。`results/documents`包括英文正文、补充材料及引用顺序。`references`包括27条EndNote RIS/XML交换库，可导入EndNote建立原生文献库；Word使用固定编号引用。`document_assets`包括模板、英文正文、作者基金信息与文献元数据。

```powershell
python predict_new.py --input "new_samples.mat" --output "results/new_predictions.csv"
```

默认模型是校正准则选择的BSRS，可通过 `--model` 指定其它比较模型。新输入必须包含X和wv，具有相同的141个波长及兼容的采集条件。新群体的准确度需通过参考测定核实。

完整流程在Python 3.12.14及锁定的依赖版本上执行；主要实际导入版本在run_summary.json记录。投稿前需作者确认稿中标记的植物鉴定、标准品、仪器型号与采集参数、含量质量基准及参考测定计算、作者贡献、利益冲突和数据公开信息。基金的中文项目英文描述可按官方指定名称替换，编号保持用户提供的值。
