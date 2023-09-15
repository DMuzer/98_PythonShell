
#  coding: utf-8 
class cl1(object) :
    def __init__(self) :
        self._a = 1

    def _set1(self, a) :
        print("Исходный сеттер")
        self._a = a
    def _get1(self) :
        print("приемник исходный")
        return self._a

    a = property(_get1, _set1)

    

class cl2(cl1) :
    def _set1(self, a):
        print('Модифицированный сеттер')
        super(cl2, self)._set1(a)


    a = property(cl1._get1, _set1)
