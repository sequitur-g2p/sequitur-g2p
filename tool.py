from __future__ import print_function

__author__ = "Maximilian Bisani"
__version__ = "$LastChangedRevision: 1668 $"
__date__ = "$LastChangedDate: 2007-06-02 18:14:47 +0200 (Sat, 02 Jun 2007) $"
__copyright__ = "Copyright (c) 2004-2005  RWTH Aachen University"
__license__ = """
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License Version 2 (June
1991) as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, you will find it at
http://www.gnu.org/licenses/gpl.html, or write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110,
USA.

Should a provision of no. 9 and 10 of the GNU General Public License
be invalid or become invalid, a valid provision is deemed to have been
agreed upon which comes closest to what the parties intended
commercially. In any case guarantee/warranty shall be limited to gross
negligent actions or intended actions or fraudulent concealment.
"""


class UsageError(RuntimeError):
    pass


def addOptions(optparser):
    optparser.add_option(
        "-p",
        "--profile",
        help="Profile execution time and store result in FILE",
        metavar="FILE",
    )
    optparser.add_option(
        "-R",
        "--resource-usage",
        action="store_true",
        help="Report resource usage execution time",
    )
    optparser.add_option(
        "-Y", "--psyco", action="store_true", help="Use Psyco to speed up execution"
    )
    optparser.add_option(
        "--tempdir", help="store temporary files in PATH", metavar="PATH"
    )


def run(main, options, args):
    import sys

    if options.tempdir:
        import tempfile, os

        if os.path.isdir(options.tempdir):
            tempfile.tempdir = options.tempdir
        else:
            raise ValueError("path does not exist", options.tempdir)

    if options.resource_usage:
        import datetime, time

        startTime = datetime.datetime.now()
        startClock = time.clock()

    try:
        status = runMain(main, options, args)
    except UsageError:
        status = 1
        print("Try '%s --help'" % sys.argv[0], file=sys.stdout)

    if options.resource_usage:
        stopTime = datetime.datetime.now()
        stopClock = time.clock()
        print("elapsed time:   ", stopTime - startTime, file=sys.stderr)
        print(
            "processor time: ",
            datetime.timedelta(seconds=stopClock - startClock),
            file=sys.stderr,
        )

    sys.exit(status)


def runMain(main, options, args):
    if options.profile:
        if True:
            import hotshot

            profile = hotshot.Profile(options.profile)
            profile.runcall(main, options, args)
            profile.close()
            import hotshot.stats

            stats = hotshot.stats.load(options.profile)
        else:
            import profile

            profile.run("main(options, args)", options.profile)
            import pstats

            stats = pstats.Stats(options.profile)
        stats.strip_dirs()
        stats.sort_stats("time", "calls")
        stats.print_stats(20)
    elif options.psyco:
        import psyco

        psyco.full()
        status = main(options, args)
    else:
        status = main(options, args)
    return status
