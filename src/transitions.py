#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

This file is part of BORIS.

  BORIS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  any later version.

  BORIS is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not see <http://www.gnu.org/licenses/>.

"""

import os
import sys
import logging


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
            if c not in unique_behaviors:
                unique_behaviors.append(c)

    unique_behaviors.sort()

    return sequences, unique_behaviors


def observed_transitions_matrix(sequences, behaviours, mode="frequency"):
    """
    create the normalized matrix of observed transitions
    mode:
    * frequency:
    * number
    * frequencies_after_behaviors
    """

    logging.debug("function: observed_transitions_matrix")
    logging.debug(f"behaviours: {behaviours}")

    if "" in behaviours:
        behaviours.remove("")

    transitions = {}
    for behaviour in behaviours:
        if not behaviour:
            continue
        transitions[behaviour] = {}
        for behaviour2 in behaviours:
            transitions[behaviour][behaviour2] = 0

    for seq in sequences:
        for i in range(len(seq) - 1):
            if not seq[i]:
                continue
            if seq[i] in behaviours and seq[i + 1] in behaviours:
                transitions[seq[i]][seq[i + 1]] += 1

    transitions_total_number = sum([sum(transitions[x].values()) for x in transitions])

    if not transitions_total_number:
        return False

    out = "\t" + "\t".join(list(behaviours)) + "\n"
    for behaviour in behaviours:
        out += "{}\t".format(behaviour)
        for behaviour2 in behaviours:
            if mode == "frequency":
                out += "{}\t".format(transitions[behaviour][behaviour2] / transitions_total_number)
            elif mode == "number":
                out += "{}\t".format(transitions[behaviour][behaviour2])
            elif mode == "frequencies_after_behaviors":
                if sum(transitions[behaviour].values()):
                    out += "{}\t".format(transitions[behaviour][behaviour2] / sum(transitions[behaviour].values()))
                else:
                    out += "{}\t".format(transitions[behaviour][behaviour2])
        out = out[:-1] + "\n"

    return out



def create_transitions_gv_from_matrix(matrix, cutoff_all=0, cutoff_behavior=0, edge_label="percent_node"):
        """
        create code for GraphViz
        matrix: matrix of frequency
        edge_label: (percent_node, fraction_node)
        return string containing graphviz code
        """

        behaviours = matrix.split("\n")[0].strip().split("\t")
        transitions = {}

        for row in matrix.split("\n")[1:]:
            if not row:
                continue

            transitions[row.split("\t")[0]] = {}
            for idx, r in enumerate(row.split("\t")[1:]):
                if '.' in r:
                    transitions[row.split("\t")[0]][behaviours[idx]] = float(r)
                else:
                    transitions[row.split("\t")[0]][behaviours[idx]] = int(r)

        transitions_total_number = sum([sum(transitions[x].values()) for x in transitions])

        out = "digraph G { \n"

        for behaviour1 in behaviours:
            for behaviour2 in behaviours:

                if transitions[behaviour1][behaviour2]:

                    if edge_label == "percent_node":
                        if transitions[behaviour1][behaviour2] > cutoff_all:
                            out += '"{behaviour1}" -> "{behaviour2}" [label="{label:0.3f}"];\n'.format(
    behaviour1=behaviour1,
    behaviour2=behaviour2,
    label=transitions[behaviour1][behaviour2])

                    if edge_label == "fraction_node":
                        transition_sum = sum(transitions[behaviour1].values())
                        if transitions[behaviour1][behaviour2] / transition_sum > cutoff_behavior:
                            out += """"{behaviour1}" -> "{behaviour2}" [label="{label}%"];\n""".format(behaviour1=behaviour1,
                                    behaviour2=behaviour2, label=round(transitions[behaviour1][behaviour2] / transition_sum * 100, 1))

        out += '\n}'
        return out
