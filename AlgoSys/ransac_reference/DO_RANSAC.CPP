/******************************************************************************/
/*                                                                            */
/* DO_RANSAC - Evaluate a candidate model                                     */
/*   This performs two steps:                                                 */
/*     1) Execute the RANSAC algorithm to find the best model                 */
/*     2) Compute the final selection criterion based on the entire dataset   */
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

/*
--------------------------------------------------------------------------------

   Generate a uniform in [0, 1).

   This version is lower (but good enough) quality and thread-safe.
   It must NEVER be called with iparam=0 and will never return 0.

--------------------------------------------------------------------------------
*/

#define IA 16807
#define IM 2147483647
#define IQ 127773
#define IR 2836

double fast_unif ( int *iparam )
{
   long k ;

   k = *iparam / IQ ;
   *iparam = IA * (*iparam - k * IQ) - IR * k ;
   if (*iparam < 0)
      *iparam += IM ;
   return *iparam / (double) IM ;
}

/*
--------------------------------------------------------------------------------

   do_ransac - Perform RANSAC algorithm

   An important note about the SingularValueDecomp object here...
   The routine fit_model() in LIN_QUAD.CPP needs this object.
   I could allocate and free it there, making cleaner code.
   But this routine is called many, many times from here, and in multiple
   threads if multi-threading is used.  That would cause an enormous amount
   of memory thrashing.  So to minimize create/delete cycles I create the
   object here and pass it as a parameter.  That's ugly, but efficient.

   A more object-oriented approach would be to have a LinQuad object whose
   constructor creates the SingularValueDecomp object, but that would
   require keeping that large, expensive object around for the life of the
   LinQuad object, even though it is needed only for training, not for
   predicting or evaluating error, which might happen over an extended period.
   So it's a tradeoff, and I made my choice.  Feel free to disagree.

--------------------------------------------------------------------------------
*/

double do_ransac (       // Returns criterion
   int ncases ,          // Number of cases in data
   int sample_size ,     // Number of cases in each sample, much smaller than ncases
   double floor ,        // Min fraction of cases traded for profit factor, -1 for RMS error   
   double noise_frac ,   // Fraction of cases assumed noise (0.01 to 0.3 or so), 0 for no RANSAC
   int termination ,     // Stop if this many failures to improve in a row
   int npred ,           // Number of predictors to use
   int *preds ,          // Their indices in data
   int ncols ,           // Number of columns (variables) in data
   double *data ,        // ncases by ncols dataset
   double *target ,      // ncases vector of targets
   int *flags ,          // Work vector ncases long
   double *coefs ,       // Coefficient vector npred + npred * (npred+1) / 2 + 1 long
   double *probs ,       // Probability vector ncases long
   double *predictions , // Work vector ncases long
   double *work1 ,       // Work vector ncases long
   double *work2         // Work vector ncases long
   )
{
   int i,  k, nvars, klo, khi, failure_count, randseed ;
   double frac, crit, best_crit, term, sum ;
   double pf_all, high_thresh, pf_high, low_thresh , pf_low ;
   SingularValueDecomp *sptr ;

   nvars = npred + npred * (npred+1) / 2 ; // Linear + quadratic


/*
--------------------------------------------------------------------------------

   This initial section handles the trivial case of the user NOT wanting RANSAC,
   which is indicated by noise_frac = 0.

--------------------------------------------------------------------------------
*/

   if (noise_frac == 0.0) {
      for (i=0 ; i<ncases ; i++)
         flags[i] = 1 ;   // Use every case

      sptr = new SingularValueDecomp ( ncases , nvars+1 , 0 ) ;
      assert ( sptr != NULL ) ;

      fit_model ( ncases , flags , npred , preds , ncols , data , target , sptr , coefs ) ;

      delete sptr ;

/*
   Compute and return the criterion.
   We are minimizing, so for profit factor return its reciprocal
*/

      if (floor < 0.0)  // User wants RMS error
         return evaluate_model ( ncases , flags , npred , preds , ncols , data , target , coefs ) ;

      predict_model ( ncases , npred , preds , ncols , data , predictions , coefs ) ;


      k = (int) (floor * ncases + 0.5) ;

      opt_pf ( ncases , k , -1 , predictions , target ,
                        &pf_all , &high_thresh , &pf_high , &low_thresh ,
                        &pf_low , work1 , work2 ) ;  // Borrow probs for work vector
      if (pf_high > pf_low)
         return 1.0 / pf_high ;
      else
         return 1.0 / pf_low ;
      }


/*
--------------------------------------------------------------------------------

   This is the actual RANSAC algorithm

--------------------------------------------------------------------------------
*/

/*
   Create the initial selection vector so all cases have equal probability
   Initialize the seed for the random generator so training is repeatable.
   Create the SingularValueDecomp object for use in the main loop.
*/

   frac = 1.0 / ncases ;
   for (i=0 ; i<ncases ; i++)
      probs[i] = i * frac ;

   randseed = 1234 ;
   fast_unif ( &randseed ) ;  // This routine is threadsafe; warm it up

   sptr = new SingularValueDecomp ( sample_size , nvars+1 , 0 ) ;
   assert ( sptr != NULL ) ;


/*
--------------------------------------------------------------------------------

   Main loop is here

--------------------------------------------------------------------------------
*/

   best_crit = 1.e60 ;
   failure_count = 0 ;

   for (;;) {

/*
   Select the training set; Identify them by setting their flags[] to 1.
   This selection is without replacement, so there are no deliberately duplicated values.
*/

      for (i=0 ; i<ncases ; i++)
         flags[i] = 0 ;

      for (i=0 ; i<sample_size ; i++) {
         frac = fast_unif ( &randseed ) ;

         // Use binary search to find the selected case
         // Bound frac between klo and khi and select case klo

         if (frac >= probs[ncases-1])  // Outside range means last case
            k = ncases - 1 ;
         else {                        // We need to do binary search
            klo = 0 ;                  // Will have probs[klo] <= frac < probs[khi]
            khi = ncases - 1 ;
   
            while (khi > klo+1) {
               k = (khi + klo) / 2 ;
               if (frac < probs[k])
                  khi = k ;
               else
                  klo = k ;
               }
            k = klo ;
            }

         if (flags[k]) {    // Was this case already selected?  Sample without replacement
            --i ;
            continue ;
            }

         flags[k] = 1 ;
         } // Selecting the training set

/*
   Compute the RANSAC criterion and check for convergence
*/

      fit_model ( ncases , flags , npred , preds , ncols , data , target , sptr , coefs ) ;
      predict_model ( ncases , npred , preds , ncols , data , predictions , coefs ) ;

      for (i=0 ; i<ncases ; i++) {
         flags[i] = i ;    // We no longer need flags, so use for sort indices
         crit = predictions[i] - target[i] ;  // Predicted minus true
         predictions[i] = fabs ( crit ) ;     // Absolute error
         }

      qsortdsi ( 0 , ncases-1 , predictions , flags ) ; // Sort errors ascending, also moving indices

      k = (int) ((1.0 - noise_frac) * (ncases + 1)) - 1 ;
      if (k > ncases - 1)      // Protect us from a careless user
         k = ncases - 1 ;
      crit = predictions[k] ;  // Criterion is max error that is not noise

      if (crit < best_crit) {
         best_crit = crit ;
         failure_count = 0 ;
         }
      else
         ++failure_count ;


/*
   Adjust the probabilities by making the noisy cases less likely to be selected
*/

      // Make probs[i] be the probability of selecting case i
      for (i=0 ; i<ncases-1 ; i++)
         probs[i] = probs[i+1] - probs[i] ;
      probs[ncases-1] = 1.0 - probs[ncases-1] ;

      // Reduce the probabilities of the noise cases
      for (i=k+1 ; i<ncases ; i++)
         probs[flags[i]] *= 0.95 ;

      // Rescale so probabilities sum to 1
      sum = 0.0 ;
      for (i=0 ; i<ncases ; i++)
         sum += probs[i] ;
      for (i=0 ; i<ncases ; i++)
         probs[i] /= sum ;

      // Cumulate
      sum = 0.0 ;
      for (i=0 ; i<ncases ; i++) {
         term = probs[i] ;
         probs[i] = sum ;
         sum += term ;
         }

      if (failure_count >= termination)
         break ;

      } // Main loop

   delete sptr ;


/*
   Our big accomplishment to this point is the probs vector.  We don't care about anything else.
   It is the cumulative probability for each case being NOT noise.
   So we difference the cumulative probabilities just as we did for adjustment.
   After doing this, the cases with smallest probability are the ones most likely to be noise.
   Sort them to identify the non-noise cases and train the model with these cases.
   This will be our final model.
   We need to preserve probs, so copy to work1 for sorting.
*/

   // Make probs[i] be the probability of selecting case i
   for (i=0 ; i<ncases-1 ; i++) {
      work1[i] = probs[i] = probs[i+1] - probs[i] ;
      flags[i] = i ;
      }

   work1[ncases-1] = probs[ncases-1] = 1.0 - probs[ncases-1] ;
   flags[ncases-1] = ncases-1 ;

   qsortdsi ( 0 , ncases-1 , work1 , flags ) ;

   // At this point, flags[0] is the index of the case having smallest probability,
   // flags[ncases-1] is that of the case having largest probability, and sorted in between.
   // Set the flags for the noisiest cases (lowest probability) to 0 and set the rest to 1.

   k = (int) (noise_frac * (ncases + 1)) ;  // Noisy cases
   
   for (i=0 ; i<k ; i++)       // Noise cases
      work1[flags[i]] = 0.0 ;
   
   for (i=k ; i<ncases ; i++)  // Non-noise cases
      work1[flags[i]] = 1.0 ;

   for (i=0 ; i<ncases ; i++)
      flags[i] = (int) work1[i] ;

   sptr = new SingularValueDecomp ( ncases-k , nvars+1 , 0 ) ;
   assert ( sptr != NULL ) ;

   fit_model ( ncases , flags , npred , preds , ncols , data , target , sptr , coefs ) ;

   delete sptr ;


/*
   Compute and return the criterion, which is based on only non-noise cases.
   We are minimizing, so for profit factor return its reciprocal
   For RMS error, consider only non-noise cases.
   For optimal profit factor, consider all cases.
*/

   if (floor < 0.0)  // User wants RMS error
      return evaluate_model ( ncases , flags , npred , preds , ncols , data , target , coefs ) ;

   predict_model ( ncases , npred , preds , ncols , data , predictions , coefs ) ;

   k = 0 ;
   for (i=0 ; i<ncases ; i++) { // Count how many cases (redundant but clear)
      if (flags[i])
         ++k ;
      }

   k = (int) (floor * k + 0.5) ;

   opt_pf ( ncases , k , -1 , predictions , target ,
                     &pf_all , &high_thresh , &pf_high , &low_thresh ,
                     &pf_low , work1 , work2 ) ;  // Borrow probs for work vector
   if (pf_high > pf_low)
      return 1.0 / pf_high ;
   else
      return 1.0 / pf_low ;
}
