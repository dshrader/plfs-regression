#!/usr/bin/env python
#
# Run a plfs regression test.

import sys,imp,os,re,subprocess
sys.path += ['./']

# Load the common.py module to get common variables.
(fp, path, desc) = imp.find_module('common', [os.getcwd()])
common = imp.load_module('common', fp, path, desc)
fp.close()

# After loading common.py, can load run_expr
import run_expr

def main(argv=None):
    """The main routine for submitting and running a test.

    Returns a list of job ids submitted for this test.
    """
    if argv == None:
        argv = sys.argv

    # Generated script
    script = "reg_test.sh"
    # Script that can be passed to experiment_management to run the
    # generated script
    input_script = "input_script.py"
    # Walltime for the job(s)
    walltime = "5:00"

    # Figure out the mounts for this test
    mounts = common.get_mountpoints()
    if mounts == None:
        print ("Error getting mounts")
        return [-1]
    # Specify two files to output tests to
    file_disable = os.getenv("MY_MPI_HOST") + ".ds_disable"
    file_enable = os.getenv("MY_MPI_HOST") + ".ds_enable"
    # Define utils directory
    utils_dir = (common.basedir + "/tests/utils/")

    # Prescript and postscript
    prescript = (common.basedir + "/tests/utils/rs_plfs_fuse_mount.sh ")
    postscript = (common.basedir + "/tests/utils/rs_plfs_fuse_umount.sh ")

    # Check MPI_CC
    mpi_cc = os.getenv("MPI_CC")
    if mpi_cc == None:
        print >>sys.stedrr, ("Env variable MPI_CC is not set. Exiting as "
            + "this is needed to compile a program.")
        return [-1]
    
    # Compile fileview-with-ds-switch.c so that it can be used in the test
    print ("Compiling fileview-with-ds-switch.c")
    try:
        retcode = subprocess.call(str(mpi_cc) + ' -o fileview-with-ds-switch fileview-with-ds-switch.c', 
            shell=True)
    except OSError, detail:
        print >>sys.stderr, ("Problem compiling fileview-with-ds-switch.c: " 
            + str(detail))
        return [-1]
    if retcode != 0:
        print >>sys.stderr, ("Compiling fileview-with-ds-switch.c failed. Return "
            "code was " + str(retcode))
        return [-1]
    else:
        print ("Compiling succeeded.")

    # Create the script
    try:
        f = open(script, 'w')
        # Write the header including statements to get the correct environment
        f.write('#!/bin/bash\n')
        f.write('source ' + str(common.basedir) + '/tests/utils/rs_env_init.sh\n')

        # Create a for loop to iterate throuh all mountpoints/paths
        mounts=' '.join(mounts)
        f.write('for mnt in ' + str(mounts) + '\n')
        f.write('do\n')
        f.write("    echo \"Running " + str(prescript) + "$mnt" + "\"\n")
        f.write("    need_to_umount=\"True\"\n")
        # The next section of code is to determine if the script needs to
        # run the unmount command. If rs_plfs_fuse_mount.sh returns with a 1,
        # this test is not going to issue the unmount command.
        f.write("    " + str(prescript) + "$mnt" + "\n")
        f.write("    ret=$?\n")
        f.write("    if [ \"$ret\" == 0 ]; then\n")
        f.write("        echo \"Mounting successful\"\n")
        f.write("        need_to_umount=\"True\"\n")
        f.write("    elif [ \"$ret\" == 1 ]; then\n")
        f.write("        echo \"Mount points already mounted.\"\n")
        f.write("        need_to_umount=\"False\"\n")
        f.write("    else\n")
        f.write("        echo \"ERROR: Something wrong with mounting.\"\n")
        f.write("        exit 1\n")
        f.write("    fi\n")

        # Generate targets
        f.write('    top=`' + str(utils_dir) + 'rs_exprmgmtrc_target_path_append.py $mnt`\n')
        f.write('    file_enable=$top/' + str(file_enable) + '\n')
        f.write('    file_disable=$top/' + str(file_disable) + '\n')
        f.write('    problem=False\n')
        f.write('    echo Creating $file_disable\n')
        f.write('    ' + str(common.runcommand) + ' -n ' + str(common.nprocs)
                + ' ' + str(common.curr_dir) + '/fileview-with-ds-switch plfs:'
                + '$file_disable disable_ds\n')
        f.write('    if [[ $? != 0 ]]; then\n')
        f.write('        echo "ERROR creating $file_disable."\n')
        f.write('        problem=True\n')
        f.write('    fi\n')
        f.write('    echo Creating $file_enable\n')
        f.write('    ' + str(common.runcommand) + ' -n ' + str(common.nprocs)
                + ' ' + str(common.curr_dir) + '/fileview-with-ds-switch plfs:'
                + '$file_enable enable_ds\n')
        f.write('    if [[ $? != 0 ]]; then\n')
        f.write('        echo "ERROR creating $file_enable."\n')
        f.write('        problem=True\n')
        f.write('    fi\n')
        f.write('\n')
        f.write('    if [ "$problem" == False ]; then\n')
        f.write('        echo "Diffing $file_disable and $file_enable"\n')
        f.write('        diff -q $file_disable $file_enable\n')
        f.write('        if [[ $? != 0 ]]; then\n')
        f.write('            echo "ERROR: $file_enable and $file_disable differ"\n')
        f.write('        fi\n')
        f.write('    fi\n')
        

        # Remove target files
        f.write('    rm -f $file_disable $file_enable\n')

        # Write into the script the script that will unmount plfs
        f.write("    if [ \"$need_to_umount\" == \"True\" ]; then\n")
        f.write("        echo \"Running " + str(postscript) + "$mnt" + "\"\n")
        f.write("        " + str(postscript) + "$mnt" + "\n")
        f.write("    fi\n")
        f.write('done\n')
        f.close()
        # Make the script executable.
        os.chmod(script, 0764)
    except (IOError, OSError), detail:
        print ("Problem with creating script " + str(script) 
            + ": " + str(detail))
        return [-1]


    # Run the script through experiment_management
    last_id = run_expr.main(['run_expr', str(common.curr_dir) + "/" + str(input_script),
        '--nprocs=' + str(common.nprocs), '--walltime=' + str(walltime), 
        '--dispatch=msub'])
    return [last_id]
    return [0]

if __name__ == "__main__":
    result = main()
    if result[-1] > 0:
        sys.exit(0)
    else:
        sys.exit(1)
