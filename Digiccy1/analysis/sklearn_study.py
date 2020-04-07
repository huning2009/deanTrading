import numpy as np

from sklearn import datasets
from sklearn import preprocessing
from sklearn import pipeline
from sklearn import impute
from sklearn import decomposition
from sklearn import feature_extraction
from sklearn import gaussian_process
from sklearn import linear_model
from sklearn import ensemble
from sklearn import cluster
from sklearn import metrics
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

"""
在numpy中，选择行/列，如果不加：，则返回的是一维数组；加上：，则返回的是二维数组
print(d[:,4:][:5])
"""
blobs, classes = datasets.make_blobs(1000,centers=3, n_features=3)
color = np.array(['r', 'g', 'b'])

kmeans = cluster.KMeans(n_clusters=3)
kmeans.fit(blobs)

fig =plt.figure()
ax = Axes3D(fig)
ax.scatter(blobs[:,0], blobs[:,1], blobs[:,2], color=color[classes])
ax.scatter(kmeans.cluster_centers_[:,0], kmeans.cluster_centers_[:,1], kmeans.cluster_centers_[:,2], color='black', marker='*')
plt.show()
"""
X, y = datasets.make_regression(1000, 2, noise=10)
n_estimator = np.arange(100, 1000, 200)
gbrs = [
    ensemble.GradientBoostingRegressor(n_estimators=estimator)
    for estimator in n_estimator
]
residuals = {}
for n, gbr in enumerate(gbrs):

    gbr.fit(X, y)
    residuals[gbr.n_estimators] = gbr.predict(X) - y
"""

# lr = linear_model.LinearRegression()
# lr.fit(X, y)
# y_preds_lr = lr.predict(X)

# gbr_residual = y_preds_gbr - y
# lr_residual = y_preds_lr - y

# print(gbr_residual.mean(), gbr_residual.var())
# print(lr_residual.mean(), lr_residual.var())



"""
X, y = datasets.make_classification(n_samples=1000, n_features=4)
lr = linear_model.LogisticRegression()
X_train = X[:-200]
X_test = X[-200:]
y_train = y[:-200]
y_test = y[-200:]

lr.fit(X_train, y_train)
y_train_preds = lr.predict(X_test)
print((y_train_preds==y_test).sum().astype(float)/ y_test.shape[0])
"""
"""
lr = linear_model.Ridge()
reg_data, reg_target = datasets.make_regression(n_samples=2000, n_features=3, effective_rank=2, noise=10)
n_bootstraps = 1000
len_data = len(reg_data)
subsample_size = np.int(len_data*0.75)
subsample = lambda: np.random.choice(np.arange(0, len_data), size=subsample_size)
cofes = np.zeros((n_bootstraps, 3))
for i in range(n_bootstraps):
    subsample_idx = subsample()
    subsample_X = reg_data[subsample_idx]
    subsample_y = reg_target[subsample_idx]

    lr.fit(subsample_X, subsample_y)
    cofes[i][0] = lr.coef_[0]
    cofes[i][1] = lr.coef_[1]
    cofes[i][2] = lr.coef_[2]
"""


"""X, y = datasets.make_regression(100000, 10,5)
sgd = linear_model.SGDRegressor()
train = np.random.choice([True, False], size=len(y), p=[.75, .25])
sgd.fit(X[train], y[train])
preds = sgd.predict(X[train])"""

# fig, ax = plt.subplots(len(n_estimator), 1)
# i = 0
# for value in residuals.values():
#     ax[i].hist(value, bins="auto", label=f"asd{i}")
# # ax[1].hist(cofes[:,1], bins='auto')
# # ax[2].hist(cofes[:,2], bins='auto')
#     ax[i].legend()
#     i += 1
# # plt.legend()
# plt.show()


"""
print(d[-5:])
text_encode = preprocessing.OneHotEncoder()
d_ft = text_encode.fit_transform(d[:, -1:])"""

# l = np.array([1,2,3,4,5]).reshape(1,-1)
# print(l.mean(axis=1))
# l_bi = preprocessing.binarize(l, threshold=l.mean(axis=1))
# print(l_bi)

"""
my_scaler = preprocessing.StandardScaler()
iris_x_tf = my_scaler.fit_transform(iris_X)
print(iris_x_tf.mean(axis=0))
print(iris_x_tf.std(axis=0))
"""


"""
dl = decomposition.DictionaryLearning(3)
iris_tf = dl.fit_transform(iris_X[::2])
print(iris_tf.shape)
print(iris_tf[:5])
"""

""" SVD
svd = decomposition.TruncatedSVD(2)
iris_X_svd = svd.fit_transform(iris_X)
print(iris_X_svd.shape)
print(iris_X_svd[:5])
"""


"""
A1_mean = [1, 1]
A1_cov = [[2, .99], [1, 1]]
A1 = np.random.multivariate_normal(A1_mean, A1_cov, 50)

A2_mean = [5, 5]
A2_cov = [[2, .99], [1, 1]]
A2 = np.random.multivariate_normal(A2_mean, A2_cov, 50)
A = np.vstack((A1, A2))
print(A1.shape)
print(A.shape)
B_mean = [5,0]
B_cov = [[.5, -1], [-.9, .5]]
B = np.random.multivariate_normal(B_mean, B_cov, 100)
AB = np.vstack((A,B))
print(AB.shape)

kpca = decomposition.KernelPCA(kernel='cosine', n_components=1)
AB_tra = kpca.fit_transform(AB)
print(AB_tra.shape)"""


""" impute.SimpleImputer
iris = datasets.load_iris()
iris_X = iris.data
print(iris_X[:5])
# masking_array = np.random.binomial(1, .25, iris_X.shape).astype(bool)

# iris_X[masking_array] = np.nan
# print(iris_X[:5])

# impute = impute.SimpleImputer()
# iris_X_prime = impute.fit_transform(iris_X)
# print(iris_X_prime[:5])

pca = decomposition.PCA(n_components=.98)
iris_pca = pca.fit_transform(iris_X)
print(iris_pca[:5])

fa = decomposition.FactorAnalysis(n_components=3)
iris_fa = fa.fit_transform(iris_X)
print(iris_fa[:5])
# print(pca.explained_variance_ratio_)
# """


# fig = plt.figure()
# plt.scatter(A1[:,0], A1[:,1], c="red")
# plt.scatter(A2[:,0], A2[:,1], c="green")
# plt.scatter(B[:,0], B[:,1], c="blue")

# plt.plot(AB_tra)
# ax = Axes3D(fig)
# ax.scatter(iris_tf[:,0], iris_tf[:,1], iris_tf[:,2])
# plt.show()


"""
# study pipeline
mat = datasets.make_spd_matrix(10)
masking_array = np.random.binomial(1,.1,mat.shape).astype(bool)
mat[masking_array] = np.nan
print(mat.shape)

impute = impute.SimpleImputer()
scaler = preprocessing.StandardScaler()

mat_imputed = impute.fit_transform(mat)
print(mat_imputed.shape)
print(mat_imputed[:4,:4])

mat_impute_scaler = scaler.fit_transform(mat_imputed)
print(mat_impute_scaler[:4,:4])
pipe = pipeline.Pipeline([('impute', impute), ('scaler', scaler)])

new_mat = pipe.fit_transform(mat)

print(np.array_equal(mat_impute_scaler, new_mat))
"""
