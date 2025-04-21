def main():
  def a():



    raise Exception([ # 1
      # 2
      # 3 long long long long long long long long long long long long long long long long long long long long
      # 4
      # 5
    ])



  class A:
    def b_long_long_long_long_long_long_long_long_long_long_long_long_long_long(): raise Exception([

    ])


  def r(*_):
    raise Exception

  def c():
    ([
      r
    ])[0]()

  def d():
    # long long long long long long long long long long long long long long long long long long
      # long long long long long long long long long long long long long long long long long long
    _ = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, r(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    # long long long long long long long long long long long long long long long long long long
      # long long long long long long long long long long long long long long long long long long


  def catch(f):
    try:
      f()
    except Exception as e:
      return e

  raise ExceptionGroup('group', [
    catch(a),
    catch(A.b_long_long_long_long_long_long_long_long_long_long_long_long_long_long),
    catch(c),
    catch(d),
  ])
