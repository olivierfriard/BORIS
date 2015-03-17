#!/usr/bin/env python
#coding:utf-8
# Purpose: observer pattern
# Created: 22.01.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT license
from __future__ import unicode_literals, print_function, division
__author__ = "mozman <mozman@gmx.at>"

try:
    from weakref import WeakSet
except ImportError:
    from weakrefset import WeakSet

class Observer(object):
    """ Simple implementation of the observer pattern for broadcasting messages
    to objects.

    For every event the subscriber object need an event handler called 'on_event_handler'
    accepting the parameter 'msg'.

    Because of the simple implementation of the algorithm it is necessary to
    register the objects an not only the listener methods, because the methods of
    different objects of the same calss have the same 'id' and managing the
    listeners in a WeakSet is not possible for different objects (you could
    only manage one table in one document instance).

    Example for event: 'save'
        # module 'one'
        import observer

        class Listener:
            def on_save_handler(self, msg):
                pass
            def get_root(self):
                return None

        listener = Listener()
        # subscribe to the 'global observer'
        observer.subscribe('save', listener)

        # module 'two'
        import observer
        # calls listener.on_save_handler(msg=None)
        observer.broadcast('save', msg=None)
    """

    def __init__(self):
        self._listeners = dict()

    def subscribe(self, event, listener_object):
        event_handler_name = "on_%s_handler" % event
        if not hasattr(listener_object, event_handler_name):
            raise AttributeError("Listener object has no '%s' event handler." % event)
        try:
            event_listeners = self._listeners[event]
        except KeyError:
            event_listeners = WeakSet()
            self._listeners[event] = event_listeners
        event_listeners.add(listener_object)

    def unsubscribe(self, event, listener_object):
        # Unsubscribing for objects which will be destroyed is not neccessary,
        # just unsubscribe objects that should not receive further messages.
        event_listeners = self._listeners[event]
        event_listeners.remove(listener_object)

    def broadcast(self, event, msg=None, root=None):
        """ Broadcast an 'event' and submit 'msg' to the listeners event handler.

        If the 'event' should only reach objects of one document, use the 'root'
        parameter (get 'root' with the get_xmlroot() method) and only objects with
        the same 'root' element receives the event.
        """

        event_handler_name = "on_%s_handler" % event
        def get_event_handler(listener):
            return getattr(listener, event_handler_name)

        def send_to_all(listener):
            handler = get_event_handler(listener)
            handler(msg=msg)

        def send_to_root(listener):
            try:
                listener_root = listener.get_xmlroot()
            except AttributeError:
                return

            if listener_root is root:
                handler = get_event_handler(listener)
                handler(msg=msg)

        try:
            event_listeners = self._listeners[event]
        except KeyError:
            # ok, because there is just no listener for this event
            # but mispelling of 'event' is an error trap
            return

        send = send_to_root if root else send_to_all
        for listener in event_listeners:
            send(listener)

    def _has_listener(self, event):
        # just for testing
        return self._count_listeners(event) > 0

    def _count_listeners(self, event):
        # just for testing
        try:
            return len(self._listeners[event])
        except KeyError:
            return 0

_global_observer = Observer()

subscribe = _global_observer.subscribe
unsubscripe = _global_observer.unsubscribe
broadcast = _global_observer.broadcast
