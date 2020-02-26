class ABC():
    aa = 11
    class Meta():
        a = 1

class AABBCC(ABC):
    b = 2

a = AABBCC()
print(a.aa)