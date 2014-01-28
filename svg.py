#!/usr/bin/env python

"""
SVG.py - Construct/display SVG scenes.

The following code is a lightweight wrapper around SVG files. The metaphor
is to construct a scene, add objects to it, and then write it to a file
to display it.


"""

import os

class Scene:

    def __init__(self, name = 'svg', height = 400, width = 400):
        self.name = name
        self.items = []
        self.height = height
        self.width = width
        return

    def add(self, item): self.items.append(item)

    def strarray(self):
        var = ["<?xml version=\"1.0\"?>\n",
               "<svg height=\"%d\" width=\"%d\" >\n" % (self.height, self.width),
               " <g style=\"fill-opacity:1.0; stroke:black;\n",
               "  stroke-width:1;\">\n"]
        for item in self.items: var += item.strarray()
        var += [" </g>\n</svg>\n"]
        return var

    def write_svg(self, filename = None):
        if filename:
            self.svgname = filename
        else:
            self.svgname = self.name + ".svg"
        file = open(self.svgname, 'w')
        file.writelines(self.strarray())
        file.close()
        return

    def svg_text(self):
        '''
        return SVG text
        '''
        return ''.join( self.strarray() )

class Path:
    def __init__(self, points, color, fill, opacity):
        self.points = points
        self.color = color   #rgb tuple in range(0,256)
        if fill:
            self.fill = colorstr(color)
        else:
            self.fill = 'none'
        self.opacity = opacity   #from 0 (transparent to 1 (solid)

        return

    def strarray(self):
        s = 'X'
        for p in self.points:
            s += 'L %s,%s ' % (str(p[0]), str(p[1]))
        s = s.replace('XL', 'M')
        return ['<path style="fill:%s;fill-rule:evenodd;stroke:%s;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:%s;fill-opacity:%s" \n' % \
                 (self.fill, colorstr(self.color), str(self.opacity), str(self.opacity)),
                'd="%s" />' % s]

class Line:
    def __init__(self, start, end, color):
        self.start = start #xy tuple
        self.end = end     #xy tuple
        self.color = color   #rgb tuple in range(0,256)
        return

    def strarray(self):
        return ["  <line x1=\"%d\" y1=\"%d\" x2=\"%d\" y2=\"%d\" style=\"stroke:%s;\"/>\n" % \
                (self.start[0], self.start[1], self.end[0], self.end[1], colorstr(self.color))]


class Circle:
    def __init__(self, center, radius, color, opacity):
        self.center = center #xy tuple
        self.radius = radius #xy tuple
        self.color = color   #rgb tuple in range(0,256)
        self.opacity = opacity   #from 0 (transparent to 1 (solid)
        return

    def strarray(self):
        return ["  <circle cx=\"%d\" cy=\"%d\" r=\"%d\"\n" % \
                (self.center[0], self.center[1], self.radius),
                "    style=\"fill:%s;fill-opacity:%s;stroke:%s;\"  />\n" % (colorstr(self.color), str(self.opacity), colorstr(self.color))]

class Rectangle:
    def __init__(self, origin, height, width, color):
        self.origin = origin
        self.height = height
        self.width = width
        self.color = color
        return

    def strarray(self):
        return ["  <rect x=\"%d\" y=\"%d\" height=\"%d\"\n" % (self.origin[0], self.origin[1], self.height),
                "    width=\"%d\" style=\"fill:%s;stroke:%s;\" />\n" % (self.width, colorstr(self.color), colorstr(self.color))]

class Text:
    def __init__(self, origin, text, size=24, rotation=0):
        self.origin = origin
        self.text = text
        self.size = size
        self.rotation = rotation
        return

    def strarray(self):
        return ["  <text x=\"%(x)d\" y=\"%(y)d\" font-size=\"%(size)d\" font-family=\"Verdana\" transform=\"rotate(%(rotation)d %(x)d,%(y)d)\">\n" % \
                {'x':self.origin[0], 'y':self.origin[1], 'size':self.size, 'rotation':self.rotation},
                "   %s\n" % self.text,
                "  </text>\n"]

    '''
    def strarray(self):
        return ["  <text  font-size=\"%d\" font-family=\"Verdana\">\n" % ( self.size),
                "<tspan x=\"%d\" y=\"%d\" rotate=\"-30\">%s</tspan></text>\n" % ( self.origin[0], self.origin[1],  self.text) ]
    '''


def colorstr(rgb): return "#%x%x%x" % (rgb[0] / 16, rgb[1] / 16, rgb[2] / 16)

