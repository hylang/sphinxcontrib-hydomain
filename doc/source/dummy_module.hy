(import [typing [Optional Tuple Dict]]
        [functools [wraps]]
        sys)

(defmacro defall [&rest symbols]
  `(setv __all__ ~(lfor sym symbols (mangle (name sym)))))

(defall a-func? Point adecorator MyError)

(defn a-func? ^int [^int a
                 &optional ^float [c 42.0]
                 &rest ^str args
                 &kwonly ^dict d
                 &kwargs ^(of Dict str int) kwargs]
  "Hello World!"
  (+ a b))

(defn adecorator [f]
  (with-decorator
    wraps
    (defn wrapped [&rest args &kwargs kwargs]
      (print "Hello World")
      (f #* args #** kwargs)))
  wrapped)

(defclass Point []
  "A two dimensional coordinate on the x/y plane"
  (defn --init-- [self x y]
    (setv self.x x
          self.y y))

  (defn distance ^float [self ^"Point" other]
    "Calculates distance between self and another point"
    1)

  #@(classmethod
      (defn duplicate ^"Point" [cls]
        "Create a copy of this point"
        (Point 1 1)))

  #@(staticmethod
      (defn manhattan-distance [x1 y1 x2 y2]
        "calculates the manhattan distance of the coordinates"
        1))

  #@(property
      (defn distance-to-origin [self]
        "Distance to the coordinate (0, 0)"
        1)))

(defclass MyError [Exception]
  (defn --init-- [self a b c]))
