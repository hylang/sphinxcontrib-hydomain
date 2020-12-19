.. hydomain documentation master file, created by
   sphinx-quickstart on Fri Dec 18 10:57:11 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Hy Domain
^^^^^^^^^^^^^^^
.. hy:module:: coordinates

* Link to :hy:class:`Point`

.. hy:class:: (Point [x y])

   * Link to :hy:meth:`distance`
   * Link to :hy:meth:`Point.midpoint`


   .. hy:classmethod:: (duplicate)

   .. hy:staticmethod:: (manhattan-distance [a b])

   .. hy:method:: (distance [^Point other])

      * Link to :hy:meth:`midpoint`

   .. hy:method:: (midpoint [^Point other])

      * Link to :hy:meth:`coordinates.Point.same?`

   .. hy:method:: (same? [^Point other])

      * Link to :hy:meth:`coordinates.Point.as-origin`


   .. hy:decoratormethod:: (as-origin)

      * Link to :hy:meth:`distance`

   .. hy:method:: distance-to-origin
      :property:

   * Link to :hy:attr:`prop attribute <.distance-to-origin>`
   * Link to :hy:meth:`prop method <.distance-to-origin>`

.. hy:currentmodule:: None

.. hy:class:: PointNoModule

.. hy:module:: coordinates.submodule

* Link to :hy:class:`Vector`

.. hy:class:: (Vector [x y z])

   * Link to :hy:class:`PointNoModule`

.. hy:function:: (foo [x y])

   :param x: param x
   :type  x: int
   :param y: param y
   :type  y: (of tuple str float)
   :returns: some numbers
   :rtype:   list


.. hy:function:: (bar ^list [^int x ^(of tuple str float) y])

   :param x: param x
   :param y: param y
   :returns: some numbers

.. hy:decorator:: (with_origin [point])

.. hy:attribute:: origin

   :type: Vector

.. hy:attribute:: attr2

   :type: :doc:`index`

.. hy:module:: exceptions

.. hy:exception:: Exception

.. hy:exception:: (ValueError [message])

.. hy:module:: object

.. hy:function:: (sum [&rest nums])

Python Domain
^^^^^^^^^^^^^^^

.. py:module:: coordinates

* Link to :py:class:`Point`

.. py:class:: Point(x y)

   * Link to :py:meth:`distance`
   * Link to :py:meth:`Point.midpoint`

   .. py:classmethod:: duplicate()

   .. py:staticmethod:: manhattan_distance(a, b)

   .. py:method:: distance(other: Point)

      * Link to :py:meth:`midpoint`

   .. py:method:: midpoint(other: Point)

      * Link to :py:meth:`coordinates.Point.is_same`

   .. py:method:: is_same(other: Point)

      * Link to :py:meth:`coordinates.Point.as_origin`

   .. py:decoratormethod:: as_origin()

      * Link to :py:meth:`distance`

   .. py:method:: distance_to_origin
      :property:

   * Link to :py:attr:`prop attribute <.distance_to_origin>`
   * Link to :py:meth:`prop method <.distance_to_origin>`

.. py:currentmodule:: None

.. py:class:: PointNoModule

.. py:module:: coordinates.submodule

* Link to :py:class:`Vector`

.. py:class:: Vector(x, y, z)

   * Link to :py:class:`PointNoModule`

.. py:function:: foo(x, y)

   :param x: param x
   :type  x: int
   :param y: param y
   :type  y: tuple(str, float)
   :returns: some numbers
   :rtype:   list


.. py:function:: bar(x: int, y: Tuple[str, float]) -> list

   :param x: param x
   :param y: param y
   :returns: some numbers

.. py:decorator:: with_origin(point)

.. py:attribute:: origin

   :type: Vector

.. py:attribute:: attr2

   :type: :doc:`index`

.. py:module:: exceptions

.. py:exception:: Exception

.. py:exception:: ValueError(message)

.. py:module:: object

.. py:function:: sum(*nums)
