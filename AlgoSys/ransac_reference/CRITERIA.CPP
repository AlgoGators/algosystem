/******************************************************************************/
/*                                                                            */
/* CRITERIA.CPP - Compute all criteria using a single thread.                 */
/*                                                                            */
/* The algorithm here is mathematically identical to that in CRITERIA_T.CPP   */
/* but it is much simpler.  You must include only ONE of these two modules    */
/* in your project.  If you want to study the algorithm, study CRITERIA.CPP.  */
/* Also, you will need CRITERIA.CPP if you are building your program on a     */
/* platform that does not support the Windows threading API.                  */
/* But if you are in Windows world you want to use CRITERIA_T.CPP because     */
/* it runs a LOT faster.                                                      */
/* If you use this routine, be sure to set MAX_THREADS to 1 in CONST.H        */
/* unless you want to waste a lot of memory.                                  */
/*                                                                            */
/******************************************************************************/

#include <stdio.h>
#include <malloc.h>
#include <string.h>
#include <math.h>
#include <float.h>
#include <stdlib.h>
#include <conio.h>
#include <assert.h>

#include "CONST.H"
#include "CLASSES.h"
#include "FUNCDEFS.H"

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
   int i, j, k, m, pred_indices[3] ;

   m = 0 ;

/*
   Do all individual models
*/

   for (i=0 ; i<n_indicators ; i++) {
      pred_indices[0] = ind_index[i] ;
      crits[m] = do_ransac ( ncases , sample_size , floor , noise_frac , termination , 1 , pred_indices ,
                             ncols , data , target , flags , coefs , probs , predictions , work1 , work2 ) ;
      ++m ;
      }

   if (npred < 2)
      return 0 ;

/*
   Do all pairs
*/

   for (i=0 ; i<n_indicators-1 ; i++) {
      for (j=i+1 ; j<n_indicators ; j++) {
         pred_indices[0] = ind_index[i] ;
         pred_indices[1] = ind_index[j] ;
         crits[m] = do_ransac ( ncases , sample_size , floor , noise_frac , termination , 2 , pred_indices ,
                                ncols , data , target , flags , coefs , probs , predictions , work1 , work2 ) ;
         ++m ;
         }
      }

   if (npred < 3)
      return 0 ;

/*
   Do all trios
*/

   for (i=0 ; i<n_indicators-2 ; i++) {
      for (j=i+1 ; j<n_indicators-1 ; j++) {
         for (k=j+1 ; k<n_indicators ; k++) {
            pred_indices[0] = ind_index[i] ;
            pred_indices[1] = ind_index[j] ;
            pred_indices[2] = ind_index[k] ;
            crits[m] = do_ransac ( ncases , sample_size , floor , noise_frac , termination , 3 , pred_indices ,
                                   ncols , data , target , flags , coefs , probs , predictions , work1 , work2 ) ;
            ++m ;
            }
         }
      }

   return 0 ;
}
