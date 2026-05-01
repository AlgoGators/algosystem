/******************************************************************************/
/*                                                                            */
/*  LIN_QUAD - Fit a linear-quadratic model                                   */
/*             Includes fit_model(), evaluate_model(), and predict_model()    */
/*                                                                            */
/*  I require the caller to supply a SingularValueDecomp object and a         */
/*  coefs work vector.  This will drive object-oriented fanatics crazy.       */
/*  A generally better approach would be to make this an object and have      */
/*  its constructor allocate these two things.  However, the SVD object       */
/*  is needed only during training, and it is big and expensive.              */
/*  So I do it this way to make it easier to allocate the SVD right before    */
/*  training and free it right after, also handling memory issues.            */
/*  Feel free to disagree and modify the code if you wish (easy).             */
/*                                                                            */
/******************************************************************************/

#include <assert.h>
#include <math.h>

#include "CONST.H"
#include "CLASSES.h"
#include "FUNCDEFS.H"



int fit_model (
   int ncases ,        // Number of cases in data
   int *flags ,        // Binary flag vector identifying cases used
   int npred ,         // Number of predictors to use
   int *preds ,        // Their indices in data
   int ncols ,         // Number of columns (variables) in data
   double *data ,      // ncases by ncols dataset
   double *target ,    // ncases vector of targets
   SingularValueDecomp *sptr ,  // Caller-supplied for use here
   double *coefs       // npred + npred * (npred+1) / 2 + 1 computed coefs
   )
{
   int icase, ivar, nvars, k1, k2 ;
   double *aptr, *bptr, *dptr ;

   nvars = npred + npred * (npred+1) / 2 ; // Linear + quadratic


/*
   Build the design matrix, decompose, and back substitute.
*/

   aptr = sptr->a ;
   bptr = sptr->b ;

   for (icase=0 ; icase<ncases ; icase++) {
      if (! flags[icase])
         continue ;

      dptr = data + icase * ncols ;
      k1 = 0 ;  // These will index the cross products
      k2 = 1 ;
      for (ivar=0 ; ivar<nvars ; ivar++) {
         if (ivar < npred)                    // Linear terms
            *aptr++ = dptr[preds[ivar]] ;
         else if (ivar < 2*npred)             // Square terms
            *aptr++ = dptr[preds[ivar-npred]] * dptr[preds[ivar-npred]] ;
         else {                               // Cross-product terms
            *aptr++ = dptr[preds[k1]] * dptr[preds[k2]] ;
            ++k2 ;
            if (k2 == npred) {
               ++k1 ;
               k2 = k1 + 1 ;
               }
            }
         }
      *aptr++ = 1.0 ;  // Constant
      }

   sptr->svdcmp () ;

   for (icase=0 ; icase<ncases ; icase++) {
      if (flags[icase])
         *bptr++ = target[icase] ;
      }

   sptr->backsub ( 1.e-7 , coefs ) ;

   return 0 ;
}


/*
--------------------------------------------------------------------------------

   Evaluate a linear-quadratic model
   This returns the RMS error

--------------------------------------------------------------------------------
*/

double evaluate_model (
   int ncases ,        // Number of cases in data
   int *flags ,        // Binary flag vector identifying cases used
   int npred ,         // Number of predictors to use
   int *preds ,        // Their indices in data
   int ncols ,         // Number of columns (variables) in data
   double *data ,      // ncases by ncols dataset
   double *target ,    // ncases vector of targets
   double *coefs       // npred + npred * (npred+1) / 2 + 1 input coefs
   )
{
   int icase, ivar, nvars, ntrain, k1, k2 ;
   double x, *dptr, pred, diff, err ;

   nvars = npred + npred * (npred+1) / 2 ; // Linear + quadratic
   ntrain = 0 ;
   for (icase=0 ; icase<ncases ; icase++) {
      if (flags[icase])
         ++ntrain ;
      }

   err = 0.0 ;
   for (icase=0 ; icase<ncases ; icase++) {
      if (! flags[icase])
         continue ;
      dptr = data + icase * ncols ;
      k1 = 0 ;  // These will index the cross products
      k2 = 1 ;
      pred = coefs[nvars] ;
      for (ivar=0 ; ivar<nvars ; ivar++) {
         if (ivar < npred)            // Linear terms
            x = dptr[preds[ivar]] ;
         else if (ivar < 2*npred)     // Square terms
            x = dptr[preds[ivar-npred]] * dptr[preds[ivar-npred]] ;
         else {                       // Cross-product terms
            x = dptr[preds[k1]] * dptr[preds[k2]] ;
            ++k2 ;
            if (k2 == npred) {
               ++k1 ;
               k2 = k1 + 1 ;
               }
            }
         pred += x * coefs[ivar] ;
         } // For ivar

      diff = pred - target[icase] ;
      err += diff * diff ;
      } // For icase

   return sqrt ( err / ntrain ) ;
}


/*
--------------------------------------------------------------------------------

   Predict with linear-quadratic model
   This returns the predictions

--------------------------------------------------------------------------------
*/

void predict_model (
   int ncases ,          // Number of cases in data
   int npred ,           // Number of predictors to use
   int *preds ,          // Their indices in data
   int ncols ,           // Number of columns (variables) in data
   double *data ,        // ncases by ncols dataset
   double *predictions , // ncases vector of targets
   double *coefs         // npred + npred * (npred+1) / 2 + 1 input coefs
   )
{
   int icase, ivar, nvars, k1, k2 ;
   double x, *dptr, pred ;

   nvars = npred + npred * (npred+1) / 2 ; // Linear + quadratic

   for (icase=0 ; icase<ncases ; icase++) {
      dptr = data + icase * ncols ;
      k1 = 0 ;  // These will index the cross products
      k2 = 1 ;
      pred = coefs[nvars] ;           // Constant term
      for (ivar=0 ; ivar<nvars ; ivar++) {
         if (ivar < npred)            // Linear terms
            x = dptr[preds[ivar]] ;
         else if (ivar < 2*npred)     // Square terms
            x = dptr[preds[ivar-npred]] * dptr[preds[ivar-npred]] ;
         else {                       // Cross-product terms
            x = dptr[preds[k1]] * dptr[preds[k2]] ;
            ++k2 ;
            if (k2 == npred) {
               ++k1 ;
               k2 = k1 + 1 ;
               }
            }
         pred += x * coefs[ivar] ;
         } // For ivar

      predictions[icase] = pred ;
      } // For icase
}