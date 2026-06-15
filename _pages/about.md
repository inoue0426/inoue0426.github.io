---
permalink: /
title: "About"
author_profile: true
redirect_from:
  - /about/
  - /about.html
---

I am a Ph.D. candidate in Computer Science at the University of Minnesota and a pre-doctoral fellow at the National Library of Medicine / National Cancer Institute.

My research develops machine learning methods for molecular medicine, focusing on drug response prediction, graph representation learning, perturbation modeling, and LLM-based biomedical reasoning for precision oncology.

Previously, I received my M.S. in Information Science from the Nara Institute of Science and Technology and was a visiting scholar at UC Davis.

## Research Interests

- Machine learning for molecular medicine
- Drug response prediction and treatment response modeling
- Graph representation learning for biological and pharmacological data
- Single-cell, perturbation, and intervention-aware representation learning
- LLM-based biomedical reasoning and evidence integration

## Selected Publications

{% assign recent_pubs = site.publications | sort: "year" | reverse %}
{% assign shown_count = 0 %}
{% for post in recent_pubs %}
  {% assign author_list = post.authors | default: "" | split: ", " %}
  {% if author_list[0] == "Yoshitaka Inoue" and shown_count < 5 %}
  {% assign paper_link = post.paperurl %}
  {% if paper_link == nil and post.url and post.url contains '://' %}
    {% assign paper_link = post.url %}
  {% endif %}
  {% assign display_authors = post.authors | default: "" | replace: "Yoshitaka Inoue", "**Yoshitaka Inoue**" %}
  {% if post.year %}
{% assign display_year = post.year %}
  {% else %}
{% assign display_year = post.date | date: "%Y" %}
  {% endif %}
- {{ post.title }} ({{ display_year }}){% if paper_link %} · [Paper]({{ paper_link }}){% endif %}<br>
  {{ display_authors }}
  {% assign shown_count = shown_count | plus: 1 %}
  {% endif %}

{% endfor %}
