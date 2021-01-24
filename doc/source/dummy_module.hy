"Dummy Python Module

some additional text"
(import [typing [Optional Tuple Dict final]]
        [functools [wraps]]
        abc
        sys)

;; TODO Module documenter doesn't pull macros
(defmacro defall [&rest symbols]
  "Defines --all-- using unmangled hy names"
  `(setv __all__ ~(lfor sym symbols (mangle (name sym)))))

(deftag ! [&rest body]
  "Tag macro for await expression"
  `(await (~@body)))

(defall a-func? Point adecorator MyError GLOBAL-VAR Vector async-func obj-param-test)

;; TODO
(setv GLOBAL-VAR "hello world")
"Something important about GLOBAL-VAR"

;; TODO Crashes compiler
;; (setv Vector (of list float))
;; "New Data Type"

;; TODO arbitrary object default parameters
;; WARNING crashes compiler
;; (setv -sentinel (object))
;; (defn obj-param-test [&optional [something -sentinel]])

(defn a-func? ^int [^int a
                 &optional ^float [c 42.0]
                 &rest ^str a!rgs
                 &kwonly ^dict d
                 &kwargs ^(of Dict str int) kwargs]
  "Hello World!"
  (+ a b))

(defn/a async-func [a])

(defn adecorator [f]
  (with-decorator
    wraps
    (defn wrapped [&rest args &kwargs kwargs]
      (print "Hello World")
      (f #* args #** kwargs)))
  wrapped)

(defclass Point []
  "A two dimensional coordinate on the x/y plane"

  ;; TODO Crashes compiler
  ;; (setv Vector (of list float))
  ;; "New Attribute Type"

  (defn --init-- [self x y]
    ;; TODO
    (setv self.x x)
    "location on the x axis"
    (setv self.y y)
    "location on the y axis")

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
        1))

  (defn/a async-method [sefl])

  #@(abc.abstractmethod
      (defn method_to_implement [self input]))

  #@(final
      (defn final-method [self]))
  )

;; TODO

#@(final
    (defclass MyError [Exception]
      (defn --init-- [self a b c])))
