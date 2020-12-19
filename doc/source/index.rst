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

   .. hy:method:: (distance [^Point other])

      * Link to :hy:meth:`midpoint`

   .. hy:method:: (midpoint [^Point other])

      * Link to :hy:meth:`coordinates.Point.same?`

   .. hy:method:: (same? [^Point other])

      * Link to :hy:meth:`coordinates.Point.distance`

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
.. py:module:: module_a.submodule

* Link to :py:class:`ModTopLevel`

.. py:class:: ModTopLevel

    * Link to :py:meth:`mod_child_1`
    * Link to :py:meth:`ModTopLevel.mod_child_1`

.. py:method:: ModTopLevel.mod_child_1

    * Link to :py:meth:`mod_child_2`

.. py:method:: ModTopLevel.mod_child_2

    * Link to :py:meth:`module_a.submodule.ModTopLevel.mod_child_1`

.. py:method:: ModTopLevel.prop
   :property:

   * Link to :py:attr:`prop attribute <.prop>`
   * Link to :py:meth:`prop method <.prop>`

.. py:currentmodule:: None

.. py:class:: ModNoModule

.. py:module:: module_b.submodule

* Link to :py:class:`ModTopLevel`

.. py:class:: ModTopLevel

    * Link to :py:class:`ModNoModule`

.. py:function:: foo(x, y)

   :param x: param x
   :type  x: int
   :param y: param y
   :type  y: tuple(str, float)
   :rtype:   list

.. py:function:: bar(x: int, y: Tuple[str, float]) -> list

.. py:attribute:: attr1

   :type: ModTopLevel

.. py:attribute:: attr2

   :type: :doc:`index`

.. py:module:: exceptions

.. py:exception:: Exception

.. py:module:: object

.. py:function:: sum()
