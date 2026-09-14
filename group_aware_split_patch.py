"""
PATCH for model/train.ipynb — Section 4 "Train classifier" cell.

WHY: the current cell uses `train_test_split(..., stratify=y)`, which splits
individual PARAGRAPHS at random. Since paragraphs from the same manuscript
share the same fonts/styles/layout conventions, this leaks document-level
information between train and test — a paragraph from document X can end up
in the training set while its neighbour from the same document X ends up in
the "test" set, so the model is partly being tested on documents it has
effectively already seen. This is why the notebook reported 100% test
accuracy but the real engine misclassifies ~35-40% of elements in brand new
manuscripts during Phase 2 integration testing.

FIX: split by DOCUMENT (source_doc) instead of by row, using GroupShuffleSplit.
Every row from a given manuscript goes entirely into either train or test,
never both. This gives an honest accuracy number that actually predicts
real-world performance on manuscripts the model has never seen.

HOW TO APPLY:
1. Open model/train.ipynb in Colab.
2. Find the cell under "## 4. Train classifier" (currently uses train_test_split).
3. Replace its contents with the code below.
4. Re-run from this cell onward, re-export artifacts (Section 6), and hand
   the new classifier.joblib + scaler.joblib to Person B.

Everything downstream (evaluate, export) stays exactly the same — only the
split changes.
"""

from sklearn.model_selection import GroupShuffleSplit, cross_val_score, cross_val_predict
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import numpy as np

# labeled_df must still have the 'source_doc' column at this point
# (it does, in the existing notebook -- it's only dropped when writing
# training_data.csv, a few cells later).

X = labeled_df[FEATURE_COLUMNS].values.astype(float)
y = labeled_df['label'].values
groups = labeled_df['source_doc'].values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Group-aware split: every row from a given document goes to ONE side only.
gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
train_idx, test_idx = next(gss.split(X_scaled, y, groups=groups))

X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
y_train, y_test = y[train_idx], y[test_idx]

print(f"Train: {len(train_idx)} rows from {len(set(groups[train_idx]))} documents")
print(f"Test:  {len(test_idx)} rows from {len(set(groups[test_idx]))} documents")
print(f"Documents in test set (should NOT overlap with train): {set(groups[test_idx])}")

clf = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42,
                              class_weight='balanced')
clf.fit(X_train, y_train)

# Group-aware cross-validation too, for a more honest CV number than plain cross_val_score(cv=5)
from sklearn.model_selection import GroupKFold
n_groups = len(set(groups))
gkf = GroupKFold(n_splits=min(5, max(2, n_groups)))
cv_scores = cross_val_score(clf, X_scaled, y, groups=groups, cv=gkf)
print(f"Group-aware CV accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

# NOTE: if accuracy drops noticeably vs. the old row-level split (it likely
# will), that's not a regression -- it's the model finally being evaluated
# honestly. Use this number in the performance-evaluation deliverable, not
# the old one.
