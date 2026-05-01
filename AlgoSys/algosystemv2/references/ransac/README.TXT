There are two criterion routines.  Only ONE of them must be included in the project!

  CRITERIA.CPP is the single-threaded version.  It is short and simple,
  and is the one to be studied if you wish to understand its operation.
  This is also the routine you must use if you are building the program on
  a platform that does not accept the Windows threading API.

  CRITERIA_T is the multi-threaded version.  It is much longer and more complex,
  although mathematically it does exactly the same thing as the single-threaded version.
  Because it is tremendously faster than the single-threaded version,
  it should be used on a Windows platform.

  Near the end of the CONST.H file there is a defined constant MAX_THREADS.
  You can set this to whatever limit you want to impose, although of course it
  should be set to 1 if you are building with the single-threaded version.
  (Setting it greater than 1 for the single-threaded version is legal but
  will require unnecessary extra memory to be allocated.)

I do all memory allocation with my thread-safe, error-checking set of routines
in MEM64.CPP.  If you use CRITERIA_T.CPP for multi-threaded operation, you must
either use my MEM64 routines or write your own thread-safe memory routines.
This is because memory is allocated and freed in individual threads.
However, if you use CRITERIA.CPP, the much slower and simpler single-threaded
version, then you can (if you wish) replace MALLOC with malloc, FREE with free,
and REALLOC with realloc.  In this case you must also remove all calls to MEMTEXT,
which I use to insert comments in the memory log file, or alternatively,
write your own memtext routine that just returns without doing anything.

This algorithm is identical to that in VarScreen, so please see that documentation
for usage details, including the format required for the market history file.

The control file is an ordinary text file that lists variable names, one per line.
The first line names the predicted variable, and the remaining lines name
the predictor candidates.

I have included demonstration market and control files, and the batch file
TEST.BAT to execute the program with fixed parameters.  This test file uses
fewer replications and termination count than would be required for serious use.
But I wanted it to run relatively quickly.

Note that unless you use upwards of a thousand MCPT replications, p-values
may significantly differ for this routine versus VarScreen due to natural
random variation.