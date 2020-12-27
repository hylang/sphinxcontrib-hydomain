(import [typing [Optional Tuple Dict]])

(defn a-func? ^int [^int a
                 &optional ^float [c 42.0]
                 &rest ^str args
                 &kwonly ^dict d
                 &kwargs ^(of Dict str int) kwargs]
  "Hello World!"
  (+ a b))

(setv CONSTANT 42)
