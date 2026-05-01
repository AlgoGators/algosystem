/******************************************************************************/
/*                                                                            */
/*  MEM64.CPP                                                                 */
/*                                                                            */
/*  This set of routines is used to intercept all calls to malloc, realloc,   */
/*  and free, checking the legality of their actions.                         */
/*  The routine memtext is also here to allow runtime commenting of the       */
/*  log file.                                                                 */
/*  Be sure to initialize as shown at the beginning of the main module.       */
/*  Finally, memclose should be called at program completion to verify that   */
/*  no memory is still dangling.                                              */
/*                                                                            */
/*  This routine requires the Windows memory API, so if you are on a          */
/*  non-Windows system you will need to supply your own memory system         */
/*  or (the simple solution!) use malloc, realloc, and free.                  */
/*  In this case you will also either need to remove all calls to memtext()   */
/*  or supply a dummy routine for it.                                         */
/*                                                                            */
/*  But please remember that CRITERIA_T uses threading, and your malloc()     */
/*  etc. may not be thread-safe!                                              */
/*                                                                            */
/******************************************************************************/

#define STRICT
#include <windows.h>
#include <commctrl.h>
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <ctype.h>
#include <malloc.h>
#include <new.h>
#include <float.h>
#include <process.h>

#include "CONST.H"
#include "CLASSES.h"
#include "FUNCDEFS.H"


HANDLE mem64heap ;

#define MAX_ALLOCS 768000

#define DEBUG_PRE_POST 0
#define DEBUG_FREE 0

/*
   These four globals must be initialized in the main program
*/

int mem_keep_log = 0 ;         // Keep a log file?
char mem_file_name[256] = "" ; // Log file name
INT64 mem_max_used=0 ;         // Maximum memory ever in use
CRITICAL_SECTION mem64_critsec ;

static int nallocs=0 ;                // Number of allocations
static INT64 allocs[MAX_ALLOCS] ;     // Ptrs to them (guaranteed mod 8) here
static INT64 actual[MAX_ALLOCS] ;     // Actual ptrs
static INT64 preptr[MAX_ALLOCS] ;     // Pointer to validation area before
static INT64 postptr[MAX_ALLOCS] ;    // and after the allocated block
static INT64 alloc_size[MAX_ALLOCS] ; // Size of those allocs
static INT64 total_use=0 ;            // Total bytes allocated
static FILE *fp_rec ;                 // File pointer for recording actions

void *memalloc ( size_t n )
{
   int k ;
   void *ptr, *ptr8, *pre, *post ;
   union {
      void *dptr ;
      INT64 cptr ;
      unsigned int ival[2] ;
      } uptr ;

   EnterCriticalSection ( &mem64_critsec ) ;

   uptr.cptr = 0 ;   // Purely for printing in Win32
   if (n == 0) {
      if (mem_keep_log) {
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nMEM.CPP: memalloc called with length=0" ) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      return NULL ;
      }

   if (nallocs == MAX_ALLOCS) {
      if (mem_keep_log) {
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nMEM.CPP: memalloc MAX_ALLOCS exceeded" ) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      return NULL ;
      }

   if (mem64heap == NULL) {
      mem64heap = HeapCreate ( 0 , 1024 * 1024 , 0 ) ;
      if (mem64heap == NULL) {
         if (mem_keep_log) {
            for (k=0 ; k<1024 ; k++) {
               if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
                  break ;
               }
            if (fp_rec != NULL) {
               fprintf ( fp_rec , "\nMEM.CPP: memalloc HeapCreate failed... ERROR!" ) ;
               fclose ( fp_rec ) ;
               }
            }
         LeaveCriticalSection ( &mem64_critsec ) ;
         return NULL ;
         }
      }

   ptr = (void *) HeapAlloc ( mem64heap , 0 , n + 4 * sizeof(INT64) ) ;

   if (ptr != NULL) {
      pre = uptr.dptr = ptr ;
      uptr.cptr += 2 * sizeof(INT64) ;
      ptr8 = uptr.dptr ;
      uptr.cptr += n ;
      post = uptr.dptr ;
      // Place unique flags before and after array to find under/overrun
      * (INT64 *) pre = (INT64) ptr ^ 12345 ;
      * (((INT64 *) pre)+1) = (INT64) ptr ^ 13579 ;
      * (INT64 *) post = (INT64) ptr ^ 67890 ;
      * (((INT64 *) post)+1) = (INT64) ptr ^ 24680 ;
      actual[nallocs] = (INT64) ptr ;
      allocs[nallocs] = (INT64) ptr8 ;
      preptr[nallocs] = (INT64) pre ;
      postptr[nallocs] = (INT64) post ;
      alloc_size[nallocs++] = n ;
      total_use += n ;
      if (total_use > mem_max_used)
         mem_max_used = total_use ;
      }

   else {
      if (mem_keep_log) {
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nAlloc = NULL... ERROR!" ) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      return NULL ;
      }

   if (mem_keep_log) {
      for (k=0 ; k<1024 ; k++) {
         if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
            break ;
         }
      if (fp_rec != NULL) {
#if DEBUG_PRE_POST
         fprintf ( fp_rec ,
            "\nAlloc=%u (%u) %u bytes  %d allocs total memory=%d (%d %d %d %d)" ,
            (unsigned) ptr8 , (unsigned) ptr , n, nallocs, total_use,
            * (int *) pre, * (((int *) pre)+1), * (int *) post,
            * (((int *) post)+1) ) ;
#else
         uptr.dptr = ptr8 ;
         fprintf ( fp_rec ,
            "\nAlloc=%u:%u  %zu bytes  %d allocs  total memory=%u MB" ,
            uptr.ival[0], uptr.ival[1] , n, nallocs,
            (unsigned) (total_use / (1024 * 1024))) ;
#endif
         fclose ( fp_rec ) ;
         }
      }

   LeaveCriticalSection ( &mem64_critsec ) ;
   return ( ptr8 ) ;
}

void memfree ( void *ptr )
{
   int i, k ;
   void *ptr_to_free ;
   union {
      void *dptr ;
      INT64 cptr ;
      unsigned int ival[2] ;
      } uptr ;

   EnterCriticalSection ( &mem64_critsec ) ;
   uptr.cptr = 0 ;   // Purely for printing in Win32

   i = nallocs ;
   while (i--) {
      if (allocs[i] == (INT64) ptr)
         break ;
      }

   if (i < 0) {
      if (mem_keep_log) {
         uptr.dptr = ptr ;
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nMEM.CPP: illegal FREE = %u:%u",
                      uptr.ival[0], uptr.ival[1]) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      exit ( 1 ) ;
      }

   if ((* (INT64 *) preptr[i] != (actual[i] ^ 12345))
    || (* (((INT64 *) preptr[i])+1) != (actual[i] ^ 13579))) {
      if (mem_keep_log) {
         uptr.dptr = ptr ;
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nMEM.CPP: FREE underrun = %u:%u",
                      uptr.ival[0], uptr.ival[1] ) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      exit ( 1 ) ;
      }

   if ((* (INT64 *) postptr[i] != (actual[i] ^ 67890))
    || (* (((INT64 *) postptr[i])+1) != (actual[i] ^ 24680))) {
      if (mem_keep_log) {
         uptr.dptr = ptr ;
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nMEM.CPP: FREE overrun = %u:%u",
                      uptr.ival[0], uptr.ival[1] ) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      exit ( 1 ) ;
      }

   --nallocs ;
   total_use -= alloc_size[i] ;
   ptr_to_free = (void *) actual[i] ;

   if (mem_keep_log) {
      uptr.dptr = ptr ;
      for (k=0 ; k<1024 ; k++) {
         if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
            break ;
         }
      if (fp_rec != NULL) {
         fprintf ( fp_rec , "\nFree=%u:%u  %d allocs  total memory=%u MB",
                   uptr.ival[0], uptr.ival[1], nallocs,
                   (unsigned) (total_use / (1024 * 1024)) ) ;
         fclose ( fp_rec ) ;
         }
      }

   while (i<nallocs) {   // Remove old ptr
      alloc_size[i] = alloc_size[i+1] ;
      allocs[i] = allocs[i+1] ;
      actual[i] = actual[i+1] ;
      preptr[i] = preptr[i+1] ;
      postptr[i] = postptr[i+1] ;
      ++i ;
      }

   HeapFree ( mem64heap , 0 , ptr_to_free ) ;
   LeaveCriticalSection ( &mem64_critsec ) ;
}

void *memrealloc ( void *ptr , size_t n )
{
   int i, k ;
   void *newptr, *ptr_to_realloc, *ptr8, *pre, *post ;
   union {
      void *dptr ;
      INT64 cptr ;
      unsigned int ival[2] ;
      } uptr, uptr2 ;

   if (ptr == NULL)
      return memalloc ( n ) ;

   EnterCriticalSection ( &mem64_critsec ) ;

   uptr.cptr = uptr2.cptr = 0 ;   // Purely for printing in Win32

   i = nallocs ;
   while (i--) {
      if (allocs[i] == (INT64) ptr) {
         ptr_to_realloc = (void *) actual[i] ;
         break ;
         }
      }

   if (i < 0) {
      if (mem_keep_log) {
         uptr.dptr = ptr ;
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nMEM.CPP: Illegal REALLOC = %u:%u",
                      uptr.ival[0], uptr.ival[1] ) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      return NULL ;
      }

   if ((* (INT64 *) preptr[i] != (actual[i] ^ 12345))
    || (* (((INT64 *) preptr[i])+1) != (actual[i] ^ 13579))) {
      if (mem_keep_log) {
         uptr.dptr = ptr ;
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nMEM.CPP: REALLOC underrun = %u:%u",
                      uptr.ival[0], uptr.ival[1] ) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      exit ( 1 ) ;
      }

   if ((* (INT64 *) postptr[i] != (actual[i] ^ 67890))
    || (* (((INT64 *) postptr[i])+1) != (actual[i] ^ 24680))) {
      if (mem_keep_log) {
         uptr.dptr = ptr ;
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nMEM.CPP: REALLOC overrun = %u:%u",
                      uptr.ival[0], uptr.ival[1] ) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      exit ( 1 ) ;
      }

   newptr = (void *) HeapReAlloc ( mem64heap , 0 , ptr_to_realloc , n + 4 * sizeof(INT64) ) ;

   pre = uptr.dptr = newptr ;
   uptr.cptr = uptr.cptr + 2 * sizeof(INT64) ;
   ptr8 = uptr.dptr ;
   uptr.cptr = uptr.cptr + n ;
   post = uptr.dptr ;

   if (mem_keep_log) {
      uptr.dptr = ptr ;
      uptr2.dptr = ptr8 ;
      for (k=0 ; k<1024 ; k++) {
         if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
            break ;
         }
      if (fp_rec != NULL) {
         fprintf ( fp_rec , "\nRealloc=%u:%u (%u:%u)  %zu bytes  total=%d MB",
                   uptr.ival[0], uptr.ival[1], uptr2.ival[0], uptr2.ival[1], n,
                   ((unsigned) total_use + (unsigned) n - (unsigned) alloc_size[i]) / (1024 * 1024)) ;
         fclose ( fp_rec ) ;
         }
      }

   if (newptr != NULL) {
      total_use = total_use + n - alloc_size[i] ;
      alloc_size[i] = n ;
      actual[i] = (INT64) newptr ;
      preptr[i] = (INT64) pre ;
      postptr[i] = (INT64) post ;
      allocs[i] = (INT64) ptr8 ;
      if (((INT64) newptr) > 0) {
         // Place unique flags before and after array to find under/overrun
         * (INT64 *) pre = (INT64) newptr ^ 12345 ;
         * (((INT64 *) pre)+1) = (INT64) newptr ^ 13579 ;
         * (INT64 *) post = (INT64) newptr ^ 67890 ;
         * (((INT64 *) post)+1) = (INT64) newptr ^ 24680 ;
         }
      if (total_use > mem_max_used)
         mem_max_used = total_use ;
#if DEBUG_PRE_POST
      if (mem_keep_log) {
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf( fp_rec, " (%d %d %d %d)",
               * (int *) pre, * (((int *) pre)+1), * (int *) post,
               * (((int *) post)+1) ) ;
            fclose ( fp_rec ) ;
            }
         }
#endif
      }

   else {
      if (mem_keep_log) {
         for (k=0 ; k<1024 ; k++) {
            if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
               break ;
            }
         if (fp_rec != NULL) {
            fprintf ( fp_rec , "\nReAlloc = NULL... ERROR!" ) ;
            fclose ( fp_rec ) ;
            }
         }
      LeaveCriticalSection ( &mem64_critsec ) ;
      return NULL ;
      }

   LeaveCriticalSection ( &mem64_critsec ) ;
   return ptr8 ;
}

void memtext ( char *text )
{
   int k ;
   SYSTEMTIME systime ;

   EnterCriticalSection ( &mem64_critsec ) ;
   if (mem_keep_log) {
      GetLocalTime ( &systime ) ;
      for (k=0 ; k<1024 ; k++) {
         if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
            break ;
         }
      if (fp_rec != NULL) {
         fprintf ( fp_rec , "\n%d:%02d:%02d:%02d  %s",
            systime.wHour, systime.wMinute, systime.wSecond, systime.wMilliseconds, text ) ;
         fclose ( fp_rec ) ;
         }
      }
   LeaveCriticalSection ( &mem64_critsec ) ;
}

void notext ( char * )
{
   return ;
}

void memclose ()
{
   int i, k ;
   union {
      void *dptr ;
      INT64 cptr ;
      unsigned int ival[2] ;
      } uptr ;

   EnterCriticalSection ( &mem64_critsec ) ;
   uptr.cptr = 0 ;   // Purely for printing in Win32

   if (mem_keep_log) {
      for (k=0 ; k<1024 ; k++) {
         if (! fopen_s ( &fp_rec , mem_file_name , "at" ))
            break ;
         }
      if (fp_rec != NULL) {
         fprintf( fp_rec , "\nMax memory use=%u MB  Dangling allocs=%d",
                  (unsigned) (mem_max_used / (1024 * 1024)), nallocs ) ;
         i = nallocs ;
         while (i--) {
            uptr.cptr = allocs[i] ;
            fprintf ( fp_rec , "\n%u:%u", uptr.ival[0], uptr.ival[1] ) ;
            }
         fclose (fp_rec ) ;
         }
      }

   HeapDestroy ( mem64heap ) ;
   mem64heap = NULL ;
   LeaveCriticalSection ( &mem64_critsec ) ;
}

void nomemclose ()
{
   return ;
}

/*
--------------------------------------------------------------------------------

   These do not do MEM.LOG writing, so they are a lot faster.
   They nonetheless avoid the malloc() CRT system

--------------------------------------------------------------------------------
*/

static HANDLE heap = NULL ;

void *memallocX ( size_t n )
{
   EnterCriticalSection ( &mem64_critsec ) ;
   if (heap == NULL) {
      heap = HeapCreate ( 0 , 1024 * 1024 , 0 ) ;
      if (heap == NULL) {
         LeaveCriticalSection ( &mem64_critsec ) ;
         return NULL ;
         }
      }

   LeaveCriticalSection ( &mem64_critsec ) ;
   return (void *) HeapAlloc ( heap , 0 , n ) ;
}

void *memreallocX ( void *ptr , size_t n )
{
   if (ptr == NULL)
      return (void *) memallocX ( n ) ;
   return (void *) HeapReAlloc ( heap , 0 , ptr , n ) ;
}

void memfreeX ( void *ptr )
{
   EnterCriticalSection ( &mem64_critsec ) ;
   HeapFree ( heap , 0 , ptr ) ;
   LeaveCriticalSection ( &mem64_critsec ) ;
}


void memcloseX ()
{
   HeapDestroy ( heap ) ;
}