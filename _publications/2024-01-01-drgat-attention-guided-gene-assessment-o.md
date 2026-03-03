---
title: "drGAT: Attention-Guided Gene Assessment of Drug Response Utilizing a Drug-Cell-Gene Heterogeneous Network"
authors: "Yoshitaka Inoue, Hunmin Lee, Tianfan Fu, Augustin Luna"
year: 2024
venue: ""
doi: "10.20944/preprints202408.1941.v1"
url: "https://doi.org/10.20944/preprints202408.1941.v1"
collection: publications
---

<jats:p>Drug development is a lengthy process with a high failure rate. Increasingly, machine learning is utilized to facilitate the drug development processes. These models aim to enhance our understanding of drug characteristics, including their activity in biological contexts. However, a major challenge in drug response (DR) prediction is model interpretability as it aids in the validation of findings. This is important in biomedicine, where models need to be understandable in comparison with established knowledge of drug interactions with proteins. drGAT, a graph deep learning model, leverages a heterogeneous graph composed of relationships between proteins, cell lines, and drugs. drGAT is designed with two objectives: DR prediction as a binary sensitivity prediction and elucidation of drug mechanism from attention coefficients. drGAT has demonstrated superior performance over existing models, achieving 78\% accuracy (and precision), and 76\% F1 score for 269 DNA-damaging compounds of the NCI60 drug response dataset. To assess the model's interpretability, we conducted a review of drug-gene co-occurrences in Pubmed abstracts in comparison to the top 5 genes with the highest attention coefficients for each drug. We also examined whether known relationships were retained in the model by inspecting the neighborhoods of topoisomerase-related drugs. For example, our model retained TOP1 as a highly weighted predictive feature for irinotecan and topotecan, in addition to other genes that could potentially be regulators of the drugs. Our method can be used to accurately predict sensitivity to drugs and may be useful in the identification of biomarkers relating to the treatment of cancer patients.</jats:p>
