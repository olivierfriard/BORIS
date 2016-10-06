import os
import sys

QTWEB = ""

try:
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    try:
        from PyQt5.QtWebKitWidgets import QWebView
        print("PyQt5.QtWebKitWidgets found")
        QTWEB = "webkit"
    except:
        print("PyQt5.QtWebKitWidgets not installed\nTrying PyQt5.QtWebEngineWidgets...")
        try:
            from PyQt5.QtCore import QEventLoop
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            print("PyQt5.QtWebEngineWidgets found")
            QTWEB = "webengine"
        except:
            print("PyQt5.QtWebEngineWidgets not installed\nTransitions flow diagram will not be available")
except:
    try:
        from PyQt4.QtCore import *
        try:
            from PyQt4.QtWebKit import QWebView
            print("PyQt4.QtWebKit found")
            QTWEB = "webkit"
        except:
            print("PyQt4.QtWebKit not installed\nTransitions flow diagram will not be available")
    except:
        pass




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

        print("behaviours", behaviours)

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


    if QTWEB == "webkit": # PyQt4 or PyQt5 < 5.6
        view = QWebView()
        frame = view.page().mainFrame()
        view.setHtml("""<script>function draw_gv(data) { var svg = Viz(data, "svg"); fromJS.text(svg) }</script>""")
        fromJS = FromJS()
        frame.addToJavaScriptWindowObject('fromJS', fromJS)

        frame.evaluateJavaScript(open("viz.js").read())
        frame.evaluateJavaScript("""draw_gv('{}')""".format(gv))

        return fromJS.txt

    if QTWEB == "webengine": # PyQt5 >= 5.6

        def render(source_html):

            class Render(QWebEngineView):
                def __init__(self, gv):
                    self.gv = gv
                    self.html = None
                    QWebEngineView.__init__(self)
                    self.loadFinished.connect(self._loadFinished)
                    self.setHtml("""<script>function draw_gv(data) { var svg = Viz(data, "svg"); document.write(svg) }</script>""")

                    while self.html is None:
                        QApplication.processEvents( QEventLoop.ExcludeUserInputEvents | QEventLoop.ExcludeSocketNotifiers | QEventLoop.WaitForMoreEvents )

                def _callable(self, data):
                    self.html = data

                def _loadFinished(self, result):

                    if os.path.isfile(sys.path[0]):  # pyinstaller
                        syspath = os.path.dirname(sys.path[0])
                    else:
                        syspath = sys.path[0]

                    if os.path.isfile(syspath + "/viz.js"):
                        self.page().runJavaScript(open("viz.js").read())
                        self.page().runJavaScript("""draw_gv('{}')""".format(self.gv))
                    self.page().toHtml(self._callable)

            result = Render(gv).html
            return result.replace("</body></html>","").replace("<html><head></head><body>","")

        return render(gv)


if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)

    print(create_diagram_from_gv("digraph G { Welcome -> To ; To -> Web; To -> GraphViz}"))
    app.exec_()
