# Model Evaluation Report

- Test accuracy: 1.000
- CV accuracy: 0.967 (+/- 0.056)

## Classification report

```
                 precision    recall  f1-score   support

          Title       1.00      1.00      1.00         1
         Author       1.00      1.00      1.00         1
Chapter Heading       1.00      1.00      1.00         5
     Subheading       1.00      1.00      1.00         6
 Body Paragraph       1.00      1.00      1.00         9
          Table       1.00      1.00      1.00         2
         Figure       1.00      1.00      1.00         2
        Caption       1.00      1.00      1.00         3
      Reference       1.00      1.00      1.00         6
           List       1.00      1.00      1.00         7

       accuracy                           1.00        42
      macro avg       1.00      1.00      1.00        42
   weighted avg       1.00      1.00      1.00        42

```

## Confusion matrix

|                 |   Title |   Author |   Chapter Heading |   Subheading |   Body Paragraph |   Table |   Figure |   Caption |   Reference |   List |
|:----------------|--------:|---------:|------------------:|-------------:|-----------------:|--------:|---------:|----------:|------------:|-------:|
| Title           |       1 |        0 |                 0 |            0 |                0 |       0 |        0 |         0 |           0 |      0 |
| Author          |       0 |        1 |                 0 |            0 |                0 |       0 |        0 |         0 |           0 |      0 |
| Chapter Heading |       0 |        0 |                 5 |            0 |                0 |       0 |        0 |         0 |           0 |      0 |
| Subheading      |       0 |        0 |                 0 |            6 |                0 |       0 |        0 |         0 |           0 |      0 |
| Body Paragraph  |       0 |        0 |                 0 |            0 |                9 |       0 |        0 |         0 |           0 |      0 |
| Table           |       0 |        0 |                 0 |            0 |                0 |       2 |        0 |         0 |           0 |      0 |
| Figure          |       0 |        0 |                 0 |            0 |                0 |       0 |        2 |         0 |           0 |      0 |
| Caption         |       0 |        0 |                 0 |            0 |                0 |       0 |        0 |         3 |           0 |      0 |
| Reference       |       0 |        0 |                 0 |            0 |                0 |       0 |        0 |         0 |           6 |      0 |
| List            |       0 |        0 |                 0 |            0 |                0 |       0 |        0 |         0 |           0 |      7 |

![confusion matrix](confusion_matrix.png)
