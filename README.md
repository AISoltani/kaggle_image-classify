# Kaggle: [iMet Collection 2021 x AIC - FGVC8](https://www.kaggle.com/c/imet-2021-fgvc8)

[![CI complete testing](https://github.com/Borda/kaggle_imet-collection/actions/workflows/ci_testing.yml/badge.svg?branch=main&event=push)](https://github.com/Borda/kaggle_imet-collection/actions/workflows/ci_testing.yml)
[![Code formatting](https://github.com/Borda/kaggle_imet-collection/actions/workflows/code-format.yml/badge.svg?branch=main&event=push)](https://github.com/Borda/kaggle_imet-collection/actions/workflows/code-format.yml)
[![codecov](https://codecov.io/gh/Borda/kaggle_imet-collection/branch/main/graph/badge.svg)](https://codecov.io/gh/Borda/kaggle_imet-collection)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Borda/kaggle_imet-collection/main.svg)](https://results.pre-commit.ci/latest/github/Borda/kaggle_imet-collection/main)


The online cataloguing information is generated by subject matter experts and includes a wide range of data. These include, but are not limited to: multiple object classifications, artist, title, period, date, medium, culture, size, provenance, geographic location, and other related museum objects within The Met’s collection.
Adding fine-grained attributes to aid in the visual understanding of the museum objects will enable the ability to search for visually related objects.

## Experimentation

### install this tooling

A simple way how to use this basic functions:
```bash
! pip install https://github.com/Borda/kaggle_iMet-collection/archive/refs/heads/main.zip
```

### run notebooks in Kaggle

* [iMet Collection with Lightning ⚡](https://www.kaggle.com/jirkaborovec/imet-with-lightning)


### run notebooks in Colab

* [Plant pathology with Lightning](https://colab.research.google.com/github/Borda/kaggle_iMet-collection/blob/main/notebooks/iMet-with-Lightning.ipynb)

I would recommend uploading the dataset to you personal gDrive and then in notebooks connect the gDrive which saves you lost of time with re-uploading dataset when ever your Colab is reset... :]

### some results

Training progress with ResNet50 with training  for 10 epochs > over 96% validation accuracy:
