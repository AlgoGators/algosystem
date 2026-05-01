/******************************************************************************/
/*                                                                            */
/* CONST.H - System and program limitation constants                          */
/*                                                                            */
/******************************************************************************/

#include <windows.h>
#include <winbase.h>     // These headers are for GlobalAlloc etc.


/*
   These control memory allocation interception for diagnostics
   These routines are all in MEM64.CPP and are not needed if
   you replace them with malloc(), realloc(), and free().
   But note that my memory routines are thread-safe via CriticalSections,
   while your installation's CRT routines may not be!
*/

#ifdef _DEBUG
#pragma check_stack(on)
#define MALLOC memalloc
#define FREE memfree
#define REALLOC memrealloc
#define MEMTEXT memtext
#define MEMCLOSE memclose
#else
#pragma check_stack(off)
#define MALLOC memallocX
#define FREE memfreeX
#define REALLOC memreallocX
#define MEMTEXT notext
#define MEMCLOSE nomemclose
#endif


#define ERROR_INSUFFICIENT_MEMORY 3   /* Any nonzero value is fine for this program */

#define MAX_THREADS 24      /* Maximum number of threads (for CRITERIA_T.CPP only) */
#define MAX_VARS 8192       /* Maximum number of variables in the file */
#define MAX_NAME_LENGTH 15  /* Maximum number of characters in name */
                            /* Some print formatting assumes this is 15 */