def main():
  class A:
    class B:
      class C:
        @staticmethod
        def d():
          raise Exception

  A.B.C.d()


main()
