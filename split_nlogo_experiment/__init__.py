#!/usr/bin/env python3
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Lukas Ahrenberg"
__author_email__ = "lukas@ahrenberg.se"
__license__ = "GPLv3"
__version__ = "0.3.2"


import sys
import os.path
import argparse
from xml.dom import minidom
import string
import csv


def expandValueSets(value_tuples):
    """
    Recursive generator giving the different combinations of variable values.

    Parameters
    ----------

    value_tuples : list
       List of tuples, each tuple is on the form
       (variable_name, [value_0, value_1, ... , value_N])
       where the value list is the possible values for that variable.

    Yields
    ------
       : Each yield results in a list of unique variable_name and value
       combination for all variables listed in the original value_tuples.

    """
    if len(value_tuples) == 1:
        for val in value_tuples[0][1]:
            yield [(value_tuples[0][0], val)]
    else:
        for val in value_tuples[0][1]:
            for vlist in expandValueSets(value_tuples[1:]):
                yield [(value_tuples[0][0], val)] + vlist


def saveExperimentToXMLFile(experiment, xmlfile):
    """
    Given an experiment XML node saves it to a file wrapped in an experiments
    tag.  The file is also furnished with DOCTYPE tag recognized by netlogo.
    File name will be the experiment name followed by the experiment number
    (zero padded), optionally prefixed.

    Parameters
    ----------

    experiment : xml node
       An experiment tag node and its children.

    xmlfile : file pointer
       File opened for writing.
    """

    xmlfile.write("""<?xml version="1.0" encoding="us-ascii"?>\n""")
    xmlfile.write("""<!DOCTYPE experiments SYSTEM "behaviorspace.dtd">\n""")
    xmlfile.write("""<experiments>\n""")
    experiment.writexml(xmlfile)
    xmlfile.write("""</experiments>\n""")


def createArrayScriptFile(script_fp,
                          nlogofile,
                          experiment,
                          numexps,
                          script_template,
                          csv_output_dir="."
                          ):
    """
    Create an array job script file from a template string.

    Parameters
    ----------

    script_fp : file pointer
       File opened for writing.

    nlogofile : string
       File name and path of the nlogo model file.
       This string will be accessible through the key {model}
       in the script_template string.

    experiment : string
       Name of the experiment.
       This string will be accessible through the key {experiment}
       in the script_template string.

    combination_nr : int
       The experiment combination number.
       This value will be accessible through the key {combination}
       in the script_template string.

    numexps : int
       Number of experiments.
       This value will be accessible through the key {numexps}

    script_template : str
       The script template string. This string will be cloned for each script
       but the following keys can be used and will have individual values.
       {model} - The value of the parameter nlogofile.
       {experiment} - The value of the parameter experiment.
       {csvfpath} - The value of the parameter csv_output_dir.

    csv_output_dir : str, optional
       Path to the directory containing the CSV files.
       keys.


    Returns
    -------

    file_name : str
       Name of the file name used for the script.

    """

    modelname = os.path.basename(nlogofile).split('.')[0]

    strformatter = string.Formatter()
    formatmap = {
        "experiment": experiment,
        "numexps": numexps,
        "model": nlogofile,
        "modelname": modelname,
        "csvfpath": csv_output_dir
        }
    # Use string formatter to go through the script template and
    # look for unknown keys. Do not replace them, but print warning.
    for _, fn, _, _ in strformatter.parse(script_template):
        if fn is not None and fn not in formatmap.keys():
            print(f"Warning: Unsupported key '{{{fn}}}' in script template. Ignoring.")
            formatmap[fn] = f"{{{fn}}}"

    script_fp.write(script_template.format(**formatmap))


def split_nlogo_experiment():
    aparser = argparse.ArgumentParser(description="Split nlogo behavioral space experiments.")
    aparser.add_argument("-n", "--nlogo_file",
                         help="NetLogo .nlogo file with the original experiment")

    # Either specify one experiment, or all experiments, but not both
    group = aparser.add_mutually_exclusive_group(required=True)
    group.add_argument("-e", "--experiment", nargs="*",
                       help="""Name of one or more experiments in the nlogo file
                            to expand. If none are given,
                            --all_experiments must be set.""")
    group.add_argument("-a", "--all_experiments", action="store_true",
                       help="""If set, all experiments in the .nlogo
                            file will be expanded.""")

    aparser.add_argument("--repetitions_per_run", type=int, default=1,
                         help="""Number of repetitions per generated experiment
                              run. If the nlogo file is set to repeat an
                              experiment N times, these will be split into N/n
                              individual experiment runs (each repeating n
                              times), where n is the argument given to this
                              switch. Note that if n does not divide N this
                              operation will result in a lower number of total
                              repetitions.""")
    aparser.add_argument("--output_dir", default="./",
                         help="Path to output directory if not current directory.")
    aparser.add_argument("--output_prefix", default="",
                         help="""Generated files are named after the
                              experiment, if set, the value given for this
                              option will be prefixed to that name.""")
    # Scripting options.
    aparser.add_argument("--create_script", dest="script_template_file",
                         help="""Tell the program to generate script files (for
                              instance PBS files) alongside the xml setup
                              files. A template file must be provided. See the
                              external documentation for more details.""")
    aparser.add_argument("--script_output_dir",
                         help="""Path to output directory for script files. If
                              not specified, the same directory as for the XML
                              setup files is used.""")
    aparser.add_argument("--csv_output_dir", help="""Path to output directory
                         where the table data from the simulations will be
                         saved. Use with script files to set output directory
                         for executed scripts. If not specified, the same
                         directory as for the xml setup files is used.""")
    aparser.add_argument("--create_run_table", action="store_true",
                         help="""Create a csv file containing a table of run
                              numbers and corresponding parameter values. Will
                              be named as the experiment but postfixed with
                              '_run_table.csv'.""")
    aparser.add_argument("--no_path_translation", action="store_true",
                         help="""Turn off automatic path translation when
                              generating scripts. Advanced use. By default all
                              file and directory paths given are translated
                              into absolute paths, and the existence of
                              directories are tested. (This is because
                              netlogo-headless.sh always run in the netlogo
                              directory, which create problems with relative
                              paths.) However automatic path translation may
                              cause problems for users who, for instance, want
                              to give paths that do yet exist, or split
                              experiments on a different file system from where
                              the simulations will run. In such cases enabling
                              this option preserves the paths given to the
                              program as they are and it is up to the user to
                              make sure these will work.""")
    aparser.add_argument("-v", "--version", action="version",
                         version=f"{__name__} {__version__}")
    aparser.add_argument("-d", "--debug", action="store_true", default=False,
                         help="Print debugging information.")

    args = aparser.parse_args()

    if args.debug:
        print(f"DEBUG: args = {args}")

    experiments_xml = ""
    try:
        with open(args.nlogo_file) as nlogof:
            # An .nlogo file contain a lot of non-xml data
            # this is a hack to ignore those lines and
            # read the experiments data into an xml string
            # that can be parsed.
            nlogo_text = nlogof.read()
            alist = nlogo_text.split("<experiments>")
            for elem in alist[1:]:
                blist = elem.split("</experiments>")
                experiments_xml += f"<experiments>{blist[0]}</experiments>\n"
    except IOError as ioe:
        print(ioe.strerror + f" '{ioe.filename}'", file=sys.stderr)
        sys.exit(ioe.errno)

    # Absolute paths.
    # We create absolute paths for some files and paths in case given relative.

    if args.no_path_translation is False:
        args.output_dir = os.path.abspath(args.output_dir)

    if args.script_output_dir is None:
        args.script_output_dir = args.output_dir
    elif args.no_path_translation is False:
        args.script_output_dir = os.path.abspath(args.script_output_dir)

    if args.csv_output_dir is None:
        args.csv_output_dir = args.output_dir
    elif args.no_path_translation is False:
        args.csv_output_dir = os.path.abspath(args.csv_output_dir)

    # This is the absolute path name of the nlogo model file.
    if args.no_path_translation is False:
        nlogo_file_abs = os.path.abspath(args.nlogo_file)
    else:
        nlogo_file_abs = args.nlogo_file

    # Check if scripts should be generated and read the template file.
    if args.script_template_file is not None:
        script_extension = os.path.splitext(args.script_template_file)[1]
        try:
            with open(args.script_template_file) as pbst:
                script_template_string = pbst.read()
        except IOError as ioe:
            print(ioe.strerror + f" '{ioe.filename}'", file=sys.stderr)
            sys.exit(ioe.errno)

            sys.stdout.write(f"tst {args.repetitions_per_run}: ")

    #
    # Start processing.
    #
    original_dom = minidom.parseString(experiments_xml)

    # Need a document to create nodes.
    # Create a new experiments document to use as container.
    experimentDoc = minidom.getDOMImplementation().createDocument(None, "experiments", None)

    # Remember which experiments were processed.
    processed_experiments = {}

    for orig_experiment in original_dom.getElementsByTagName("experiment"):
        orig_exp_name = orig_experiment.getAttribute("name")
        if args.all_experiments or (orig_exp_name in args.experiment):

            experiment = orig_experiment.cloneNode(deep=True)

            if args.debug:
                print(f"DEBUG: orig_exp_name = {orig_exp_name}")
                print(f"DEBUG: experiment = {experiment}")

            # Store tuples of varying variables and their possible values.
            value_tuples = []
            num_individual_runs = 1

            # Number of repetitions in the experiment.
            # Read original value first. Default is to have all internal.
            reps_in_experiment = int(experiment.getAttribute("repetitions"))

            # Repeats of the created experiment.
            reps_of_experiment = 1

            # Check if we should split experiments.
            # An unset switch or value <= 0 means no splitting.
            if args.repetitions_per_run > 0:
                original_reps = int(experiment.getAttribute("repetitions"))

                if args.debug:
                    print(f"DEBUG: args.repetitions_per_run = {args.repetitions_per_run}")
                    print(f"DEBUG: original_reps = {original_reps}")
                    print("")

                if original_reps >= args.repetitions_per_run:
                    reps_in_experiment = args.repetitions_per_run
                    reps_of_experiment = original_reps // reps_in_experiment
                    if (original_reps % reps_in_experiment) != 0:
                        print(("Warning: Number of repetitions per "
                               "experiment does not divide the number of "
                               "repetitions in the nlogo file. New number of "
                               "repetitions is "
                               f"{(reps_in_experiment*reps_of_experiment)} "
                               f"({reps_in_experiment} "
                               "per experiment in "
                               f"{reps_of_experiment} "
                               "unique script(s)). Original number of "
                               "repetitions per experiment: {original_reps}."),
                              file=sys.stderr)

            # Handle enumeratedValueSets
            for evs in experiment.getElementsByTagName("enumeratedValueSet"):
                values = evs.getElementsByTagName("value")

                # If an enumeratedValueSet has more than a single value, it
                # should be included in the value expansion tuples.
                if len(values) > 1:
                    # A tuple is the name of the variable and
                    # A list of all the values.
                    value_tuples.append((evs.getAttribute("variable"),
                                         [val.getAttribute("value") for val in values]))
                    num_individual_runs *= len(value_tuples[-1][1])

                    # Remove the node.
                    experiment.removeChild(evs)

            # Handle steppedValueSet. These are integers (Java BigDecimal),
            # and inclusive of last value.
            for svs in experiment.getElementsByTagName("steppedValueSet"):
                first = int(svs.getAttribute("first"))
                last = int(svs.getAttribute("last"))
                step = int(svs.getAttribute("step"))

                # Add values to the tuple list.
                value_tuples.append((svs.getAttribute("variable"),
                                     [x for x in range(first, last+1, step)]))
                num_individual_runs *= len(value_tuples[-1][1])

                # Remove node.
                experiment.removeChild(svs)

            # Now create the different individual runs.
            enum = 1

            # Keep track of the parameter values in a run table.
            run_table = []
            ENR_STR = "Experiment number"
            if num_individual_runs > 1:
                vsgen = expandValueSets(value_tuples)
            else:
                # If there were no experiments to expand create a dummy-
                # expansion just to make sure the single experiment is still
                # created.
                vsgen = [[]]

            for exp in vsgen:
                for exp_clone in range(reps_of_experiment):
                    # Add header in case we are on the first row.
                    if enum == 1:
                        run_table.append([ENR_STR])
                    run_table.append([enum])

                    experiment_instance = experiment.cloneNode(deep=True)
                    experiment_instance.setAttribute("repetitions", str(reps_in_experiment))
                    for evs_name, evs_value in exp:
                        evs = experimentDoc.createElement("enumeratedValueSet")
                        evs.setAttribute("variable", evs_name)
                        vnode = experimentDoc.createElement("value")
                        vnode.setAttribute("value", str(evs_value))
                        evs.appendChild(vnode)
                        experiment_instance.appendChild(evs)

                        # Add header in case we are on first pass.
                        if enum == 1:
                            run_table[0].append(evs_name)

                        # Always add the current value.
                        run_table[-1].append(evs_value)

                    # Replace some special characters (including space) with
                    # chars that may cause problems in a file name.
                    # This is NOT fail safe right now. Assuming some form of
                    # useful experiment naming practice.
                    experiment_name = experiment_instance.getAttribute("name").replace(' ', '_').replace('/', '-').replace('\\', '-')
                    xml_filename = os.path.join(args.output_dir,
                                                args.output_prefix + experiment_name
                                                + '_'
                                                + str(enum).zfill(len(str(num_individual_runs)))
                                                + '.xml')
                    try:
                        with open(xml_filename, 'w') as xmlfile:
                            saveExperimentToXMLFile(experiment_instance, xmlfile)
                    except IOError as ioe:
                        print(ioe.strerror + f" '{ioe.filename}'",
                              file=sys.stderr)
                        sys.exit(ioe.errno)

                    enum += 1

                processed_experiments[orig_exp_name] = (enum - 1)

            # Check if the run table should be saved.
            if args.create_run_table:
                run_table_file_name = os.path.join(args.output_dir,
                                                   args.output_prefix
                                                   + experiment_name
                                                   + "_run_table.csv")
                try:
                    with open(run_table_file_name, 'w') as run_table_file:
                        rt_csv_writer = csv.writer(run_table_file)
                        for row in run_table:
                            rt_csv_writer.writerow(row)
                except IOError as ioe:
                    print(ioe.strerror + f" '{ioe.filename}'", file=sys.stderr)
                    sys.exit(ioe.errno)

    # Should a script file be created?
    # Want one array job script per experiment, to cover all
    # repetitions and all value sets of an experiment.
    # Each job script needs:
    # * experiment
    # * number of repetitions of experiment
    if args.debug:
        print(f"DEBUG: No. of processed experiments = {len(processed_experiments)}")

    for experiment_name, numexps in processed_experiments.items():
        if args.debug:
            print(f"DEBUG: experiment_name = {experiment_name}, numexps = {numexps}")
            print()

        if args.script_template_file is not None:
            script_file_name = os.path.join(args.script_output_dir,
                                            args.output_prefix
                                            + experiment_name
                                            + "_script"
                                            + script_extension)
            try:
                print(f'DEBUG: numexps = {numexps}')
                with open(script_file_name, 'w') as scriptfile:
                    createArrayScriptFile(
                        scriptfile,
                        nlogo_file_abs,
                        experiment_name,
                        numexps,
                        script_template_string,
                        csv_output_dir=args.csv_output_dir)
            except IOError as ioe:
                print(ioe.strerror + f" '{ioe.filename}'", file=sys.stderr)
                sys.exit(ioe.errno)

    # Warn if some experiments could not be found in the file.
    if args.experiment:
        for ename in args.experiment:
            if ename not in processed_experiments:
                print((f"Warning - Experiment named '{ename}' "
                       f"not found in model file '{args.nlogo_file}'"))


