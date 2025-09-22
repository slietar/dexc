import dexc.autoinstall

class A:
  def __del__(self):
    raise Exception


a = A()
