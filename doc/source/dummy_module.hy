"Dummy Python Module

some additional text"
(import [typing [Optional Tuple Dict final List]]
        [functools [wraps]]
        abc
        sys)

;; TODO Module documenter doesn't pull macros
(defmacro defall [#* symbols]
  "Defines `--all--` using unmangled hy names"
  `(setv __all__ ~(lfor sym symbols (mangle sym))))

(defmacro optionalmacro [a [b None]])

(defn optionalfunc ^(of List int) [a [b None]])

(defmacro ! [#* body]
  "Macro version of shortened await"
  `(await (~@body)))

(defmacro "#!" [#* body]
  "Tag macro for await expression"
  `(await (~@body)))

(defmacro/g! gensymmacro [#* body]
  "hello world!"
  None)

(defmacro triple-1 [n]
  "hello world"
  `(+ ~n ~n ~n))

(defn ^ [a b]
  "hello world")


(defall
  optionalfunc
  a-func? Point adecorator MyError GLOBAL-VAR Vector async-func obj-param-test optional-bug ^)

;; TODO
(setv GLOBAL-VAR "hello world")
"Something important about GLOBAL-VAR"

;; TODO Crashes compiler
;; (setv Vector (of list float))
;; "New Data Type"

;; TODO arbitrary object default parameters
;; WARNING crashes compiler
(setv -sentinel (object))
(defn obj-param-test [[something -sentinel]])

(defn optional-bug [[g "G"]])

(defn a-func? ^int [^int a
                 ^float [c 42.0]
                 ^str #* a!rgs
                 ^dict d
                 ^(of Dict str int) #** kwargs]
  "Hello World!"
  (+ a b))

(defn/a async-func [a])

(defn adecorator [f]
  (with-decorator
    wraps
    (defn wrapped [#* args #** kwargs]
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

  (defn/a async-method [self])

  #@(abc.abstractmethod
      (defn method_to_implement [self input]))

  #@(final
      (defn final-method [self]))
  )

;; TODO

#@(final
    (defclass MyError [Exception]
      (defn --init-- [self a b c])))
