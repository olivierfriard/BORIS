import sys

try:
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtWebKitWidgets import QWebView
except:
    try:
        from PyQt4.QtCore import *
        from PyQt4.QtWebKit import QWebView
    except:
        sys.exit()


import os


def behavioral_strings_analysis(strings, behaviouralStringsSeparator):
    """
    Analyze behavioral strings
    """

    rows = strings[:]

    sequences = []

    for row in rows:

        if behaviouralStringsSeparator:
            r = row.strip().split(behaviouralStringsSeparator)
        else:
            r = list(row.strip())

        sequences.append(r)

    # extract unique behaviors
    unique_behaviors = []
    for seq in sequences:
        for c in seq:
            if not c in unique_behaviors:
                unique_behaviors.append(c)

    unique_behaviors.sort()

    return sequences, unique_behaviors


def observed_transition_normalized_matrix(sequences, behaviours):
    """
    create the normalized matrix of observed transitions
    """

    transitions = {}
    for behaviour in behaviours:
        transitions[behaviour] = {}
        for behaviour2 in behaviours:
            transitions[behaviour][behaviour2] = 0

    for seq in sequences:
        for i in range(len(seq) - 1):
            if seq[i] in behaviours and seq[i + 1] in behaviours:
                transitions[seq[i]][seq[i + 1]] += 1

    transitions_total_number = sum([sum(transitions[x].values()) for x in transitions])

    out = '\t' + '\t'.join( list(behaviours)) + os.linesep
    for behaviour in behaviours:
        out += "{}\t".format(behaviour)
        for behaviour2 in behaviours:
            out += "{}\t".format(round(transitions[behaviour][behaviour2] / transitions_total_number, 3))
        out = out[:-1] + os.linesep

    return out


def create_transitions_gv_from_matrix(matrix, cutoff_all=0, cutoff_behavior=0, edge_label="percent_node"):
        """
        create code for GraphViz
        return string containing graphviz code
        """

        behaviours = matrix.split(os.linesep)[0].strip().split("\t")

        transitions = {}

        for row in matrix.split(os.linesep)[1:]:

            if not row:
                continue

            transitions[row.split("\t")[0]] = {}
            for idx, r in enumerate(row.split("\t")[1:]):
                transitions[row.split("\t")[0]][ behaviours[idx] ] = float(r)

        transitions_total_number = sum([sum(transitions[x].values()) for x in transitions])

        out = "digraph G { "
        out += """graph [bgcolor="#ffffff00"] """

        for behaviour1 in behaviours:
            for behaviour2 in behaviours:

                if transitions[behaviour1][behaviour2]:

                    if edge_label == "percent_node":
                        if transitions[behaviour1][behaviour2] > cutoff_all:
                            out += """"{}" -> "{}" [label="{}"];""".format(behaviour1, behaviour2, transitions[behaviour1][behaviour2])

                    if edge_label == "fraction_node":

                        transition_sum = sum(transitions[behaviour1].values())
                        if transitions[behaviour1][behaviour2] / transition_sum > cutoff_behavior:
                            out += """"{}" -> "{}" [label="{}%"];""".format(behaviour1, behaviour2, round(transitions[behaviour1][behaviour2] / transition_sum * 100, 1))

        out += '}'
        return out




def create_diagram_from_gv(gv):
    """
    create diagram from Graphviz language using viz.js
    https://github.com/mdaines/viz.js/
    """

    class FromJS(QObject):
        def __init__(self, parent=None):
            super(FromJS, self).__init__(parent)

        @pyqtSlot(str)
        def text(self, message):
            self.txt = message

    html = """<script>function draw_gv(data) { var svg = Viz(data, "svg"); fromJS.text(svg) }</script>"""
    view = QWebView()
    frame = view.page().mainFrame()
    view.setHtml(html)
    fromJS = FromJS()
    frame.addToJavaScriptWindowObject('fromJS', fromJS)

    frame.evaluateJavaScript(open("viz.js").read())
    frame.evaluateJavaScript("""draw_gv('{}')""".format(gv))

    return fromJS.txt



