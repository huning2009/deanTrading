import numpy as np

from sklearn import datasets
from sklearn import preprocessing
from sklearn import pipeline
from sklearn import impute
from sklearn import decomposition
from sklearn import feature_extraction
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

iris = datasets.load_iris()
X = iris.data
Y = iris.target
d = np.column_stack((X,Y))

"""
在numpy中，选择行/列，如果不加：，则返回的是一维数组；加上：，则返回的是二维数组
print(d[:,4:][:5])
"""
lb = preprocessing.LabelBinarizer(neg_label=-100, pos_label=100)
new_Y = lb.fit_transform(Y)
print(new_Y)





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

""" KernalPCA
A1_mean = [1, 1]
A1_cov = [[2, .99], [1, 1]]
A1 = np.random.multivariate_normal(A1_mean, A1_cov, 50)

A2_mean = [5, 5]
A2_cov = [[2, .99], [1, 1]]
A2 = np.random.multivariate_normal(A2_mean, A2_cov, 50)
A = np.vstack((A1, A2))
print(A1[:3])
print(A[:3])
B_mean = [5,0]
B_cov = [[.5, -1], [-.9, .5]]
B = np.random.multivariate_normal(B_mean, B_cov, 100)
AB = np.vstack((A,B))
print(AB.shape)

kpca = decomposition.KernelPCA(kernel='cosine', n_components=1)
AB_tra = kpca.fit_transform(AB)
print(AB_tra.shape)
"""

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