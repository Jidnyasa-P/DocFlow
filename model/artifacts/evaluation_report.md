# Model Evaluation Report

- Test accuracy: 0.967
- CV accuracy: 0.990 (+/- 0.013)

## Classification report

```
                 precision    recall  f1-score   support

          Title       1.00      1.00      1.00         3
         Author       1.00      1.00      1.00         3
Chapter Heading       1.00      0.60      0.75        15
     Subheading       0.50      1.00      0.67         6
 Body Paragraph       1.00      1.00      1.00        80
          Table       1.00      1.00      1.00         8
         Figure       1.00      1.00      1.00         2
        Caption       1.00      1.00      1.00        14
      Reference       1.00      1.00      1.00        15
           List       1.00      1.00      1.00        36

       accuracy                           0.97       182
      macro avg       0.95      0.96      0.94       182
   weighted avg       0.98      0.97      0.97       182

```

## Confusion matrix

|                 |   Title |   Author |   Chapter Heading |   Subheading |   Body Paragraph |   Table |   Figure |   Caption |   Reference |   List |
|:----------------|--------:|---------:|------------------:|-------------:|-----------------:|--------:|---------:|----------:|------------:|-------:|
| Title           |       3 |        0 |                 0 |            0 |                0 |       0 |        0 |         0 |           0 |      0 |
| Author          |       0 |        3 |                 0 |            0 |                0 |       0 |        0 |         0 |           0 |      0 |
| Chapter Heading |       0 |        0 |                 9 |            6 |                0 |       0 |        0 |         0 |           0 |      0 |
| Subheading      |       0 |        0 |                 0 |            6 |                0 |       0 |        0 |         0 |           0 |      0 |
| Body Paragraph  |       0 |        0 |                 0 |            0 |               80 |       0 |        0 |         0 |           0 |      0 |
| Table           |       0 |        0 |                 0 |            0 |                0 |       8 |        0 |         0 |           0 |      0 |
| Figure          |       0 |        0 |                 0 |            0 |                0 |       0 |        2 |         0 |           0 |      0 |
| Caption         |       0 |        0 |                 0 |            0 |                0 |       0 |        0 |        14 |           0 |      0 |
| Reference       |       0 |        0 |                 0 |            0 |                0 |       0 |        0 |         0 |          15 |      0 |
| List            |       0 |        0 |                 0 |            0 |                0 |       0 |        0 |         0 |           0 |     36 |

![confusion matrix](confusion_matrix.png)
