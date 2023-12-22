import unittest
print("hello world")
print("---")
n = None
v = None
for n, v in globals().items() :
    print("{} : {}".format(n,v))

import sys
print(sys.version)
print(sys.executable)

class Mapping :
    def get(self, key) :
        raise NotImplementedError
    def put(self, key, value) :
        raise NotImplementedError
    def __len__(self) :
        raise NotImplementedError
    def _entryiter(self) :
        raise NotImplementedError
    def __iter__(self) :
        return (e.key for e in self._entryiter())
    def values(self) :
        return (e.value for e in self._entryiter())
    def items(self) :
        return ((e.key, e.value) for e in self._entryiter())
    def __contains__(self) :
        try :
            self.get(key)
        except KeyError :
            return False
    def __getitem__(self) :
        return self.get(key)
    def __setitem__(self, key, value) :
        print("_setItem {} {}".format(key, value))
        self.put(key, value)
    def __str__(self) :
        return "{" + " ,".join(str(e) for e in self._entryiter())+ "}"



class BSTMapping(Mapping) :
    def __init__(self) :
        self._root = None 
    def get(self, key) :
        if self._root :
            return self._root.get(key).value 
        raise KeyError
    def put(self, key, value) :
        print("BSTMapping.put  : {} : {}".format(key, value))
        if self._root :
            print("roon not None")
            # self._root = 
            self._root.put(key, value)
        else :
            print('root None создаем новый')
            self._root = BSTNode(key, value)
            print(self._root)

    def __len__(self) :
        return len(self._root) if self._root is not None else 0
    def _entryiter(self) :
        if self._root :
            yield from self._root
    def floor(self, key) :
        if self._root :
            floornode = self._root.floor(key)
            if floornode is not None :
                return floornode.key, floornode.value
        return None, None 
    def remove(self, key) :
        if self._root :
            self._root = self._root.remove(key)
        else :
            raise KeyError
    def __delitem__(self, key) :
        self.remove(key)

class BSTNode(object) :
    def __init__(self, key, value) :
        print("BSTNode.__init__")
        self.key        = key
        self.value      = value
        self.left       = None
        self.right      = None 
        self._length    = 1 
    def __len__(self) :
        return self._length
    def __str__(self) :
        return str(self.key) + " : " + str(self.value)
    def get(self, key) :
        if key == self.key :
            return self
        elif key < self.key and self.left :
            return self.left.get(key)
        elif key > self.key and self.right :
            return self.right.get(key)
        else :
            raise KeyError
    def put(self, key, value) :
        print("BSTNode.__put__")
        if key == self.key :
            self.value = value
        elif key < self.key :
            if self.left :
                self.left.put(key, value)
            else :
                self.left = BSTNode(key, value)
        elif key > self.key :
            if self.right :
                self.right.put(key, value)
            else :
                print("add new right")
                self.right = BSTNode(key, value)
        self._updatelength()

    def _updatelength(self) :
        if self.left :
            self.left._updatelength()
            len_left = len(self.left) 
        else : len_left =  0
        if self.right :
            len_right = len(self.right) 
        else :
            len_right = 0
        self._length = 1 + len_left + len_right

    def floor(self, key) :
        if key == self.key :
            return self
        elif key < self.key :
            if self.left is not None :
                return self.left.floor(key)
            else :
                return None
        elif key > self.key :
            if self.right is not None :
                return self.right.floor(key)
            else :
                return self 
            
    def __iter__(self) :
        if self.left is not None :
            yield from self.left
        yield self
        if self.right is not None :
            yield from self.right
    def _swapwith(self, other) :
        self.key, other.key = other.key, self.key 
        self.value, other.value = other.value, self.value
    def maxnode(self) :
        return self.right.maxnode if self.right else self 

    def remove(self, key) :
        if key == self.key :
            if self.left is None : return self.right
            if self.right is None : return self.left
            self._swapwith(self.left.maxnode())
            self.left = self.left.remove(key)
        elif key < self.key and self.left :
            self.left = self.left.remove(key)
        elif key > self.key and self.right :
            self.right = self.right.remove(key)
        else : raise KeyError
        self._updatelength()
        return self 
    
class Test1(unittest.TestCase) :
    def test1(self) :
        T = BSTMapping()
        self.assertIsNone(T._root)
        T[1] = 1
        self.assertIsNotNone(T._root)
        self.assertEqual(len(T), 1)
        print(T)
        T2 = BSTMapping()
        self.assertIsNone(T2._root)
        T2[1] = 1
        print(T2) 
        self.assertIsNotNone(T2._root)
        self.assertEqual(len(T), 1)
        T2[5] = 5 
        self.assertIsNotNone(T2._root)
        self.assertEqual(len(T2), 2)
        T2[0] = 5
        self.assertEqual(len(T2), 3)

        print(T2)


    @unittest.skip("while")
    def test2(self) :
        T = BSTMapping()
        for i in [3,2,1,6,4,5,9,8,10, 12] :
            T[i] = None 

        print(T)
        print(T._root)
        for n in T :
            print(n)

    def test3(self) :
        T = BSTMapping()
        keys = [3,2,4,5,6,7,10,0]

        for key in keys :
            T[key] = key * 5

        for key, value in T.items() :
            print(key, value)
            self.assertEqual(key * 5, value)



unittest.main()


        

