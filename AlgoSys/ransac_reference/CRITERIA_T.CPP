/******************************************************************************/
/*                                                                            */
/* CRITERIA_T.CPP - Compute all criteria using multiple threads               */
/*                                                                            */
/* The algorithm here is mathematically identical to that in CRITERIA.CPP but */
/* it is much more complex.  You must include only ONE of these two modules   */
/* in your project.  If you want to study the algorithm, study CRITERIA.CPP.  */
/* Also, you will need CRITERIA.CPP if you are building your program on a     */
/* platform that does not support the Windows threading API.                  */
/* But if you are in Windows world you want to use CRITERIA_T.CPP because     */
/* it runs a LOT faster.                                                      */
/* MAX_THREADS in CONST.H sets the maximum number of threads allowed.         */
/*                                                                            */
/******************************************************************************/

#include <windows.h>
#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include <math.h>
#include <float.h>
#include <stdlib.h>
#include <conio.h>
#include <assert.h>
#include <process.h>

#include "CONST.H"
#include "CLASSES.h"
#include "FUNCDEFS.H"

#define DEBUG_THREADS 0


/*
--------------------------------------------------------------------------------

   Thread stuff...  Structure for passing information to/from threaded code
                    called by the main subroutine

--------------------------------------------------------------------------------
*/

typedef struct {
   int model_num ;       // Index of this model
   int ncases ;          // Number of cases in data
   int sample_size ;     // Number of cases in each sample; much smaller than ncases
   double floor ;        // Min fraction of cases traded for profit factor; -1 for RMS error   
   double noise_frac ;   // Fraction of cases assumed noise (0.01 to 0.3 or so); 0 for no RANSAC !!!!!!
   int termination ;     // Stop if this many failures to improve in a row
   int npred ;           // Number of predictors to use
   int preds[3] ;        // Their indices in data
   int ncols ;           // Number of columns (variables) in data
   double *data ;        // ncases by ncols dataset
   double *target ;      // ncases vector of targets
   int *flags ;          // Work vector ncases long
   double *coefs ;       // Coefficient vector npred + npred * (npred+1) / 2 + 1 long
   double *probs ;       // Probability vector ncases long
   double *predictions ; // Work vector ncases long
   double *work1 ;       // Work vector ncases long
   double *work2 ;       // Work vector ncases long
   double *crits ;       // Returned criteria (n_competitors in RANSAC.CPP)
} CRITERIA_PARAMS ;

/*
   This is the routine that runs in threads
   It evaluates a single model
*/

static unsigned int __stdcall criteria_threaded ( LPVOID dp )
{
   double crit ;

   crit = do_ransac ( ((CRITERIA_PARAMS *) dp)->ncases ,
                      ((CRITERIA_PARAMS *) dp)->sample_size ,
                      ((CRITERIA_PARAMS *) dp)->floor ,
                      ((CRITERIA_PARAMS *) dp)->noise_frac ,
                      ((CRITERIA_PARAMS *) dp)->termination ,
                      ((CRITERIA_PARAMS *) dp)->npred ,
                      ((CRITERIA_PARAMS *) dp)->preds ,
                      ((CRITERIA_PARAMS *) dp)->ncols ,
                      ((CRITERIA_PARAMS *) dp)->data ,
                      ((CRITERIA_PARAMS *) dp)->target ,
                      ((CRITERIA_PARAMS *) dp)->flags ,
                      ((CRITERIA_PARAMS *) dp)->coefs ,
                      ((CRITERIA_PARAMS *) dp)->probs ,
                      ((CRITERIA_PARAMS *) dp)->predictions ,
                      ((CRITERIA_PARAMS *) dp)->work1 ,
                      ((CRITERIA_PARAMS *) dp)->work2 ) ;


   ((CRITERIA_PARAMS *) dp)->crits[((CRITERIA_PARAMS *) dp)->model_num] = crit ;
   return 0 ;
}


/*
--------------------------------------------------------------------------------

   Use threading to compute all criteria

   NOTE ON THREADS... If the thread workload is low, overhead will keep CPU time
                      low.  If debug printing, one may see that only the first
                      thread keeps ending and getting replaced.  Threading behaves
                      as expected only when each thread uses a lot of CPU time.

--------------------------------------------------------------------------------
*/

int criteria (
   int ncases ,          // Number of rows in data matrix
   int *flags ,          // Work vector ncases long
   int sample_size ,     // Number of cases in each sample, much smaller than ncases
   double floor ,        // Min fraction of cases traded for profit factor, -1 for RMS error   
   double noise_frac ,   // Fraction of cases assumed noise (0.01 to 0.3 or so)
   int termination ,     // Stop if this many failures to improve in a row
   int npred ,           // Number of simultaneous predictors (1-3)
   int n_indicators ,    // Number of candidate indicators
   int ncols ,           // Number of columns in data matrix
   int *ind_index ,      // n_indicators array of column indices of indicators in data
   double *data ,        // ncases by ncols data matrix contains indicators (and maybe more)
   double *target ,      // ncases target vector
   double *coefs ,       // work array for LIN_QUAD.CPP; npred + npred * (npred+1) / 2 + 1 long
   double *probs ,       // Work vector ncases long
   double *predictions , // Work vector ncases long
   double *work1 ,       // Work vector ncases long
   double *work2 ,       // Work vector ncases long
   double *crits )       // Returned criteria (n_competitors in RANSAC.CPP)
{
   int i, k, ret_val, ithread, max_threads, n_threads, empty_slot ;
   int n_competitors, icomp, this_npred, this_0, this_1, this_2 ;
   char msg[4096] ;
   CRITERIA_PARAMS criteria_params[MAX_THREADS] ;
   HANDLE threads[MAX_THREADS] ;

   // Compute the number of competitors (models)

   n_competitors = n_indicators ;  // Number of individuals
   if (npred > 1)  // Add in pairs
      n_competitors += n_indicators * (n_indicators-1) / 2 ;
   if (npred > 2)  // Add in trios
      n_competitors += n_indicators * (n_indicators-1) * (n_indicators-2) / 6 ;

/*
   Initialize those thread parameters which are constant for all threads.
   Each thread will have its own private scratch storage.
*/

   max_threads = MAX_THREADS ;

   for (ithread=0 ; ithread<max_threads ; ithread++) {
      criteria_params[ithread].ncases = ncases ;
      criteria_params[ithread].sample_size = sample_size ;
      criteria_params[ithread].floor = floor ;
      criteria_params[ithread].noise_frac = noise_frac ;
      criteria_params[ithread].termination = termination ;
      criteria_params[ithread].ncols = ncols ;
      criteria_params[ithread].data = data ;
      criteria_params[ithread].target = target ;
      criteria_params[ithread].flags = flags + ithread * ncases ;
      criteria_params[ithread].coefs = coefs + ithread * (npred + npred * (npred+1) / 2 + 1) ;
      criteria_params[ithread].probs = probs + ithread * ncases ;
      criteria_params[ithread].predictions = predictions + ithread * ncases ;
      criteria_params[ithread].work1 = work1 + ithread * ncases ;
      criteria_params[ithread].work2 = work2 + ithread * ncases ;
      criteria_params[ithread].crits = crits ;
      } // For all threads, initializing constant stuff


/*
   Do it
*/

   n_threads = 0 ;                    // Counts threads that are active
   for (i=0 ; i<max_threads ; i++)
      threads[i] = NULL ;

   empty_slot = -1 ;  // After full, will identify the thread that just completed

   // This is the first model
   icomp = 0;
   this_npred = 1 ;
   this_0 = 0 ;
   this_1 = 0 ;
   this_2 = 0 ;
   
   for (;;) {         // Main thread loop processes all competitors
      
      
#if 0
/*
   Handle user ESCape

   If you want to check for the user pressing the ESCape key,
   this is a good place to do it, before starting a new thread.
   I don't do it, so I have removed this section from compilation,
   but I left the code here to show you how to clean up.
*/

      if (escape_key_pressed  ||  user_pressed_escape ()) {
         for (i=0, k=0 ; i<max_threads ; i++) {  // Compress all threads into a contiguous set
            if (threads[i] != NULL)
               threads[k++] = threads[i] ;
            }
         ret_val = WaitForMultipleObjects ( k , threads , TRUE , INFINITE ) ;
         sprintf_s ( msg, "CRITERIA_T.CPP: User abort; n_threads=%d  k=%d  Wait retval=%d", n_threads, k, ret_val ) ;
         MEMTEXT ( msg ) ;
         for (i=0 ; i<k ; i++) {
            CloseHandle ( threads[i] ) ;
            threads[i] = NULL ;
            }
         return ERROR_ESCAPE ;
         }
#endif


/*
   Start a new thread if we still have work to do
*/

      if (icomp < n_competitors) {  // If there are still some to do
         if (empty_slot < 0)        // Negative while we are initially filling the queue
            k = n_threads ;
         else
            k = empty_slot ;
         criteria_params[k].model_num = icomp  ;   // Needed for placing final result
         criteria_params[k].npred = this_npred  ;
         criteria_params[k].preds[0] = ind_index[this_0]  ;
         criteria_params[k].preds[1] = ind_index[this_1]  ;
         criteria_params[k].preds[2] = ind_index[this_2]  ;
         threads[k] = (HANDLE) _beginthreadex ( NULL , 0 , criteria_threaded , &criteria_params[k] , 0 , NULL ) ;
         if (threads[k] == NULL) {
            MEMTEXT ( "Internal ERROR: bad thread creation in CRITERIA_T2" ) ;
            for (i=0 ; i<n_threads ; i++) {
               if (threads[i] != NULL) {
                  CloseHandle ( threads[i] ) ;
                  threads[i] = NULL ;
                  }
               }
            return ERROR_INSUFFICIENT_MEMORY ;
            }
#if DEBUG_THREADS
         sprintf_s ( msg, "Starting icomp=%3d npred=%d (%d %d %d) Thread %8d (k=%2d n_threads=%2d)",
                   icomp, this_npred, this_0, this_1, this_2, (int) threads[k], k, n_threads ) ;
         MEMTEXT ( msg ) ;
#endif
         ++n_threads ;

         // Advance to the next model (combination of predictors)

         ++icomp ;                          // This is the model index
         if (icomp < n_indicators)          // Single variable
            ++this_0 ;
         else if (icomp == n_indicators) {  // Pairs starting
            this_npred = 2 ;
            this_0 = 0 ;
            this_1 = 1 ;
            }
         else if (icomp < n_indicators + n_indicators * (n_indicators-1) / 2) { // Pairs
            ++this_1 ;
            if (this_1 == n_indicators) {
               ++this_0 ;
               this_1 = this_0 + 1 ;
               }
            }
         else if (icomp == n_indicators + n_indicators * (n_indicators-1) / 2) { // Trios starting
            this_npred = 3 ;
            this_0 = 0 ;
            this_1 = 1 ;
            this_2 = 2 ;
            }
         else {
            ++this_2 ;
            if (this_2 == n_indicators) {
               ++this_1 ;
               this_2 = this_1 + 1 ;
               if (this_1 == n_indicators-1) {
                  ++this_0 ;
                  this_1 = this_0 + 1 ;
                  this_2 = this_1 + 1 ;
                  }
               }
            }

         } // if (icomp < n_competitors)

      if (n_threads == 0)  // Are we done?
         break ;

/*
   Handle full suite of threads running and more threads to add as soon as some are done.
   Wait for just one thread to finish.
*/

      if (n_threads == max_threads  &&  icomp < n_competitors) {
         ret_val = WaitForMultipleObjects ( n_threads , threads , FALSE , INFINITE ) ;
         if (ret_val == WAIT_TIMEOUT  ||  ret_val == WAIT_FAILED  ||  ret_val < 0  ||  ret_val >= n_threads) {
            for (i=0 ; i<n_threads ; i++) {
               if (threads[i] != NULL) {
                  CloseHandle ( threads[i] ) ;
                  threads[i] = NULL ;
                  }
               }
            sprintf_s ( msg, "INTERNAL ERROR!!!  Thread wait failed (%d) in CRITERIA_T2", ret_val ) ;
            MEMTEXT ( msg ) ;
            return ERROR_INSUFFICIENT_MEMORY ;
            }

#if DEBUG_THREADS
         sprintf_s ( msg, "End Thread %8d (%2d)  model_num=%d  f=%.3lf",
         (int) threads[ret_val], ret_val, criteria_params[ret_val].model_num,
         criteria_params[ret_val].crits[criteria_params[ret_val].model_num] ) ;
         MEMTEXT ( msg ) ;
#endif

         empty_slot = ret_val ;
         CloseHandle ( threads[empty_slot] ) ;
         threads[empty_slot] = NULL ;
         --n_threads ;
         }

/*
   Handle all work has been started and now we are just waiting for threads to finish
*/

      else if (icomp == n_competitors) {
         ret_val = WaitForMultipleObjects ( n_threads , threads , TRUE , INFINITE ) ;
         if (ret_val == WAIT_TIMEOUT  ||  ret_val == WAIT_FAILED  ||  ret_val < 0  ||  ret_val >= n_threads) {
            for (i=0 ; i<n_threads ; i++) {
               if (threads[i] != NULL) {
                  CloseHandle ( threads[i] ) ;
                  threads[i] = NULL ;
                  }
               }
            sprintf_s ( msg, "INTERNAL ERROR!!!  Thread wait failed (%d) in CRITERIA_T.CPP", ret_val ) ;
            MEMTEXT ( msg ) ;
            return ERROR_INSUFFICIENT_MEMORY ;
            }

         for (i=0 ; i<n_threads ; i++) {
#if DEBUG_THREADS
            sprintf_s ( msg, "Final Thread %8d  model_num=%d  f=%.3lf",
            (int) threads[i], criteria_params[i].model_num,
            criteria_params[i].crits[criteria_params[i].model_num] ) ;
            MEMTEXT ( msg ) ;
#endif
            CloseHandle ( threads[i] ) ;
            }
         break ;
         }
      } // Endless loop which threads computation of criterion for all predictors

   return 0 ;
}