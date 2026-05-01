/******************************************************************************/
/*                                                                            */
/* RANSAC - Use RANSAC algorithm to find effective predictors.                */
/*    This employs a linear-quadratic model, which combines moderate          */
/*    nonlinearity with fast and deterministic training.                      */
/*    To employ a different model replace the routines in LIN_QUAD.CPP.       */
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

#define MAX_LINE 128  /* Max length of a control file line; extremely conservative */

// These are defined in MEM64.CPP and are not needed if you use your own memory
// allocation sytem or revert to malloc/realloc/free.
// But do note that those CRT routines are NOT always threadsafe, so if you use the
// threaded routine CRITERIA_T.CPP you must have thread-safe memory routines!

extern int mem_keep_log ;
extern char mem_file_name[256] ;
extern INT64 mem_max_used ;
extern CRITICAL_SECTION mem64_critsec ;

/*
--------------------------------------------------------------------------------

   Main routine

--------------------------------------------------------------------------------
*/

int main (
   int argc ,    // Number of command line arguments (includes prog name)
   char *argv[]  // Arguments (prog name is argv[0])
   )
{
   int i, j, k, k1, k2, m, ivar, ret_val, irep, nreps, mcpt_type, nvars, ncases, n_indicators, npred, target_index, *ind_index ;
   int n_competitors, *solo_count, *unbiased_count, *sort_indices, modnum, id, *flags ;
   int sample_size, termination, best_npred, best_preds[3], nterms ;
   double alpha, floor, *data, diff, mean, stddev, *target_work, *model_work, *probs, *predictions, *dwork1, *dwork2 ;
   double *crits, *original_crits, best_crit, pval, prior, dummy ;
   double noise_frac ;
   char *lptr, data_filename[4096], control_filename[4096], **names, line[MAX_LINE] ;
   FILE *fp, *fp_log ;
   SYSTEMTIME systime ;

/*
   Process command line parameters
*/

   if (argc != 10) {
      printf ( "\nUsage: RANSAC  floor  alpha  noise nreps  npred  samp  term  data_filename  control_filename" ) ;
      printf ( "\n  floor - Minimum fraction (0-0.5) of cases that trade (for profit factor crit only)" ) ;
      printf ( "\n          -1 for RMS error criterion" ) ;
      printf ( "\n  alpha - Familywise alpha level (0-1, generally 0.01-0.1)" ) ;
      printf ( "\n  noise - Fraction of cases possible noise (0-0.5, generally .05 or so)" ) ;
      printf ( "\n  nreps - Number of MCPT replications (hundreds or thousands)" ) ;
      printf ( "\n  npred - Max number of predictors in model (1-3)" ) ;
      printf ( "\n  samp -  Sample size (typically one-tenth to half the number of cases)" ) ;
      printf ( "\n  term -  Terminate sampling when this many failures to improve in a row (5-100 or so)" ) ;
      printf ( "\n  data_filename - Name of database file" ) ;
      printf ( "\n  control_filename - Name of file that specifies target and indicators" ) ;
      exit ( 1 ) ;
      }

   floor = atof ( argv[1] ) ;
   alpha = atof ( argv[2] ) ;
   noise_frac = atof ( argv[3] ) ;
   nreps = atoi ( argv[4] ) ;
   npred = atoi ( argv[5] ) ;
   sample_size = atoi ( argv[6] ) ;
   termination = atoi ( argv[7] ) ;
   strcpy_s ( data_filename , argv[8] ) ;
   strcpy_s ( control_filename , argv[9] ) ;

   mcpt_type = 1 ;  // Could make this a user parameter, but we have enough already!


   if (floor >= 1.0  ||  alpha <= 0.0  ||  alpha > 1.0  || noise_frac < 0.0  ||  noise_frac >= 1.0  || nreps < 0  ||
       npred < 1  ||  npred > 3  ||  sample_size < 2  ||  termination < 1) {
      printf ( "\nUsage: RANSAC  floor  alpha  noise nreps  npred  samp  term  data_filename  control_filename" ) ;
      printf ( "\n  floor - Minimum fraction (0-0.5) of cases that trade (for profit factor crit only)" ) ;
      printf ( "\n          -1 for RMS error criterion" ) ;
      printf ( "\n  alpha - Familywise alpha level (0-1, generally 0.01-0.1)" ) ;
      printf ( "\n  noise - Fraction of cases possible noise (0-0.5, generally .05 or so)" ) ;
      printf ( "\n  nreps - Number of MCPT replications (hundreds or thousands)" ) ;
      printf ( "\n  npred - Max number of predictors in model (1-3)" ) ;
      printf ( "\n  samp -  Sample size (typically one-tenth to half the number of cases)" ) ;
      printf ( "\n  term -  Terminate sampling when this many failures to improve in a row (5-100 or so)" ) ;
      printf ( "\n  data_filename - Name of database file" ) ;
      printf ( "\n  control_filename - Name of file that specifies target and indicators" ) ;
      exit ( 1 ) ;
      }


/*
   Memory checking stuff
   This is for my error-checking memory allocation routines (MEM64.CPP)
   and is not needed if CRT routines are used instead.
   However, the multi-threaded version REQUIRES my MEM64 routines!
   This is because the CRT malloc/free is not thread-safe under some conditions.
*/

   mem_max_used = 0 ;
   mem_keep_log = 1 ;
   _fullpath ( mem_file_name , "MEM.LOG" , 256 ) ;
   if (fopen_s ( &fp , mem_file_name , "wt" )) {
      mem_file_name[0] = 0 ;
      mem_keep_log = 0 ;
      }
   else {
      GetLocalTime ( &systime ) ;
      sprintf_s ( line , "RANSAC memory log %s  %d/%d/%02d  %d:%02d:%02d" ,
         mem_file_name,
         systime.wMonth, systime.wDay, systime.wYear%100,
         systime.wHour, systime.wMinute, systime.wSecond ) ;
      fprintf ( fp , "%s", line ) ;
      fclose ( fp ) ;
      }

   InitializeCriticalSection ( &mem64_critsec ) ;  // Needed by MEM64.cpp to be thread-safe!


/*
   These initializations let us do a clean exit.
   Open the log file for writing.
*/

   nvars = 0 ;
   ind_index = NULL ;
   flags = NULL ;
   crits = NULL ;
   original_crits = NULL ;
   predictions = NULL ;
   dwork1 = NULL ;
   dwork2 = NULL ;
   target_work = NULL ;
   probs = NULL ;
   model_work = NULL ;
   solo_count = NULL ;
   unbiased_count = NULL ;
   sort_indices = NULL ;

   if (fopen_s ( &fp_log , "RANSAC.LOG" , "wt" )) {
      printf ( "\nERROR... Unable to open log file RANSAC.LOG for writing." ) ;
      goto FINISH ;
      }

   // Print user parameters in log file

   GetLocalTime ( &systime ) ;
   fprintf ( fp_log , "RANSAC result log   %d/%d/%02d  %d:%02d:%02d" ,
      systime.wMonth, systime.wDay, systime.wYear%100,
      systime.wHour, systime.wMinute, systime.wSecond ) ;
   fprintf ( fp_log, "\n  floor = %.3lf", floor ) ;
   fprintf ( fp_log, "\n  alpha = %.4lf", alpha ) ;
   fprintf ( fp_log, "\n  noise = %.4lf", noise_frac ) ;
   fprintf ( fp_log, "\n  nreps = %d", nreps ) ;
   fprintf ( fp_log, "\n  npred = %d", npred ) ;
   fprintf ( fp_log, "\n  samp = %d", sample_size ) ;
   fprintf ( fp_log, "\n  term = %d", termination ) ;
   fprintf ( fp_log, "\n  data_filename = %s", data_filename ) ;
   fprintf ( fp_log, "\n  control_filename = %s", control_filename ) ;


/*
   Read dataset and allocate some memory.
   The readfile() routine allocates all required memory (names and data).
   This memory will be freed later by a call to free_data().
*/

   ret_val = readfile ( data_filename , &nvars , &names , &ncases , &data ) ;
   if (ret_val) {
      printf ( "\nAborting due to error reading file" ) ;
      goto FINISH ;
      }

   fprintf ( fp_log , "\n\nRead %d records of %d variables each from %s",
             ncases, nvars, data_filename ) ;

   if (sample_size > ncases / 2) {
      sample_size = ncases / 2 ;
      fprintf ( fp_log , "\n\nWARNING... Sample size reduced to %d", sample_size ) ;
      }

   ind_index = (int *) MALLOC ( nvars * sizeof(int) ) ;
   if (ind_index == NULL) {
      printf ( "\nERROR... Insufficient memory" ) ;
      goto FINISH ;
      }


/*
   Read the control file.
   The first line is the target, and subsequent lines are the indicators (predictors).
*/

   if (fopen_s ( &fp , control_filename , "rt" )) {
      printf ( "\nERROR... Unable to open control file %s", control_filename ) ;
      free_data ( nvars , names , data ) ;  // Frees memory allocated by readfile() (names and data)
      goto FINISH ;
      }

   target_index = -1 ;  // Not needed; shuts up LINT
   for (n_indicators=-1 ; ; n_indicators++) {

      if ((fgets ( line , MAX_LINE , fp ) == NULL) || (strlen ( line ) < 2)) {
         if (ferror ( fp )  ||  n_indicators < 1) {
            fclose ( fp ) ;
            printf ( "\nERROR... Problem reading control file %s", control_filename ) ;
            free_data ( nvars , names , data ) ;  // Frees memory allocated by readfile() (names and data)
            goto FINISH ;
            }
         else
            break ;       // Normal end of file
         } // If error or normal end of file
      line[MAX_LINE-1] = 0 ;   // Insurance: terminate the line as a string

      // Terminate the string that names a variable
      lptr = line ;
      while (isalnum(*lptr) || *lptr == '_') // Variable names can be alphanumeric or underscore
         ++lptr ;
      *lptr = 0 ;       // Terminate this name
      _strupr_s ( line ) ;

      // Find this name in dataset variable name array
      for (ivar=0 ; ivar<nvars ; ivar++) {
         if (! strcmp ( line , names[ivar] ))
            break ;
         }
      if (ivar >= nvars) {
         printf ( "\nERROR... Variable '%s' is not in dataset", line ) ;
         free_data ( nvars , names , data ) ;  // Frees memory allocated by readfile() (names and data)
         goto FINISH ;
         }
      if (n_indicators == -1) {
         target_index = ivar ;
         fprintf ( fp_log , "\n\nTarget is %s\nIndicators...", line ) ;
         }
      else {
         ind_index[n_indicators] = ivar ;
         fprintf ( fp_log , "\n  %s", line ) ;
         }
         
      } // For reading all control file lines

   fclose ( fp ) ;


/*
   Compute and print means and standard deviations for user's edification.
   This formatting assumes that MAX_NAME_LENGTH is 15.
*/

   fprintf ( fp_log , "\n\nMeans and standard deviations...\n" ) ;
   fprintf ( fp_log , "       Variable       Mean        StdDev" ) ;

   for (ivar=-1 ; ivar<n_indicators ; ivar++) {

      if (ivar == -1)
         k = target_index ;
      else
         k = ind_index[ivar] ;

      mean = 0.0 ;
      for (i=0 ; i<ncases ; i++)
         mean += data[i*nvars+k] ;
      mean /= ncases ;

      stddev = 0.0 ;
      for (i=0 ; i<ncases ; i++) {
         diff = data[i*nvars+k] - mean ;
         stddev += diff * diff ;
         }
      stddev = sqrt ( stddev / ncases ) ;

      fprintf ( fp_log , "\n%15s %12.5lf %12.5lf", names[k], mean, stddev ) ;
      }

   fprintf ( fp_log , "\n" ) ;
 
/*
   Compute how many competitors we will have.
   Allocate all remaining memory that we will need.
*/

   if (npred > n_indicators)
      npred = n_indicators ;

   n_competitors = n_indicators ;  // Number of individuals
   if (npred > 1)  // Add in pairs
      n_competitors += n_indicators * (n_indicators-1) / 2 ;
   if (npred > 2)  // Add in trios
      n_competitors += n_indicators * (n_indicators-1) * (n_indicators-2) / 6 ;

   crits = (double *) MALLOC ( n_competitors * sizeof(double) ) ;
   original_crits = (double *) MALLOC ( n_competitors * sizeof(double) ) ;
   target_work = (double *) MALLOC ( ncases * sizeof(double) ) ;
   probs = (double *) MALLOC ( MAX_THREADS * ncases * sizeof(double) ) ;
   flags = (int *) MALLOC ( MAX_THREADS * ncases * sizeof(int) ) ;
   model_work = (double *) MALLOC ( MAX_THREADS * (npred + npred * (npred+1) / 2 + 1) * sizeof(double) ) ;
   solo_count = (int *) MALLOC ( n_competitors * sizeof(int) ) ;
   unbiased_count = (int *) MALLOC ( n_competitors * sizeof(int) ) ;
   sort_indices = (int *) MALLOC ( n_competitors * sizeof(int) ) ;
   predictions = (double *) MALLOC ( MAX_THREADS * ncases * sizeof(double) ) ;
   dwork1 = (double *) MALLOC ( MAX_THREADS * ncases * sizeof(double) ) ;
   dwork2 = (double *) MALLOC ( MAX_THREADS * ncases * sizeof(double) ) ;
   if (crits == NULL  ||  original_crits == NULL  ||  solo_count == NULL  ||  unbiased_count == NULL  || sort_indices == NULL
    || predictions == NULL  ||  dwork1 == NULL  ||  dwork2 == NULL  ||  target_work == NULL  ||  flags == NULL
    ||  probs == NULL  ||  model_work == NULL) {
      printf ( "\nERROR... Insufficient memory" ) ;
      free_data ( nvars , names , data ) ;  // Frees memory allocated by readfile() (names and data)
      goto FINISH ;
      }


/*
--------------------------------------------------------------------------------

   Outer-most loop does MCPT replications

--------------------------------------------------------------------------------
*/

   if (nreps < 1)
      nreps = 1 ;

   for (i=0 ; i<ncases ; i++)
      target_work[i] = data[i*nvars+target_index] ;

   for (irep=0 ; irep<nreps ; irep++) {
         
/*
   Shuffle target(s) if in permutation run (irep>0)
*/

      if (irep) {                  // If doing permuted runs, shuffle

         if (mcpt_type == 1) {     // Complete
            i = ncases ;           // Number remaining to be shuffled
            while (i > 1) {        // While at least 2 left to shuffle
               j = (int) (unifrand () * i) ;
               if (j >= i)
                  j = i - 1 ;
               dummy = target_work[--i] ;
               target_work[i] = target_work[j] ;
               target_work[j] = dummy ;
               }
            } // Type 1, complete

         else if (mcpt_type == 2) { // Cyclic
            j = (int) (unifrand () * ncases) ;
            if (j >= ncases)
               j = ncases - 1 ;
            for (i=0 ; i<ncases ; i++)
               dwork1[i] = target_work[(i+j)%ncases] ;
            for (i=0 ; i<ncases ; i++)
               target_work[i] = dwork1[i]  ;
            } // Type 2, cyclic

         } // If in permutation run (irep > 0)


/*
-----------------------------------------------------------------------------------

   Compute and save criterion for all combinations.

   Then update permutation tests

-----------------------------------------------------------------------------------
*/

      if (nreps > 1) {
         if (irep == 0)
             printf ( "\n\nUnpermuted pass..." ) ;
         else
             printf ( "\nPermuted pass %d of %d...", irep, nreps-1 ) ;
         }

      criteria ( ncases , flags , sample_size , floor , noise_frac , termination , npred , n_indicators , nvars ,
                 ind_index , data , target_work , model_work , probs , predictions , dwork1 , dwork2 , crits ) ;

      if (irep == 0) {
         for (i=0 ; i<n_competitors ; i++) {
            original_crits[i] = crits[i] ;
            sort_indices[i] = i ;
            solo_count[i] = 1 ;
            unbiased_count[i] = 1 ;
            }
         qsortdsi ( 0 , n_competitors-1 , crits , sort_indices ) ;
         }

      else {
         best_crit = 1.e60 ;
         for (i=n_competitors-1 ; i>=0 ; i--) {  // Process worst error to best
            if (crits[i] <= original_crits[i])
               ++solo_count[i] ;
            k = sort_indices[i] ;                // Index of i'th worst competitor
            if (crits[i] < best_crit)
               best_crit = crits[i] ;
            if (best_crit <= original_crits[k])
               ++unbiased_count[k] ;
            }
         }

      } // For all replications


/*
-----------------------------------------------------------------------------------

   Print selection results

   n_indicators is the number of indicators as specified in the control file
   n_competitors is the number of competing models
   npred is the maximum number of indicators in a model, 1-3

   n_competitors = n_indicators ;  // Number of individuals
   if (npred > 1)  // Add in pairs
      n_competitors += n_indicators * (n_indicators-1) / 2 ;
   if (npred > 2)  // Add in trios
      n_competitors += n_indicators * (n_indicators-1) * (n_indicators-2) / 6 ;

   ind_index[k] is the column in the database of indicator k.
   names[m] is the name of the variable in column m of the database.

-----------------------------------------------------------------------------------
*/

   if (floor >= 0.0) {   // If profit factor, criterion was its reciprocal because we minimize
      for (i=0 ; i<n_competitors ; i++)
         original_crits[i] = 1.0 / original_crits[i] ;
      }

   fprintf ( fp_log , "\n\nCriteria for all competitors" ) ;
   fprintf ( fp_log , "\n\n    Variable(s)   Criterion" ) ;
   if (nreps > 1)
      fprintf ( fp_log , "  Solo pval  Unbiased pval" ) ;

   prior = 0.0 ;
   best_npred = 0 ;  // Flag unusual case of best model not meeting alpha
   for (modnum=0 ; modnum<n_competitors ; modnum++) {  // From best (minimum error) to worst
      if (modnum > 500) {
         fprintf ( fp_log , "\n\nWe reached the arbitrary limit of 500 models printed; stopping here" ) ;
         break ;
         }

      id = sort_indices[modnum] ;                      // Index in crits of this competitor

      pval = (double) unbiased_count[id] / (double) nreps ;
      if (pval < prior)
         pval = prior ;
      if (nreps < 2)
         pval = 0.0 ;   // pval is undefined if no MCPT
      prior = pval ;
      if (pval > alpha) {
         fprintf ( fp_log, "\n\nBest remaining p-value=%.4lf while alpha=%.4lf, so quitting", pval, alpha ) ;
         break ;
         }

      // The complex code from here to RANSAC_PRINTED prints exactly one model (modnum)
      m = 0 ;
      for (i=0 ; i<n_indicators ; i++) {
         if (m++ == id) {
            fprintf ( fp_log , "\n\n%15s %10.4lf", names[ind_index[i]], original_crits[id] ) ;
            if (nreps > 1)
               fprintf ( fp_log , " %10.4lf %10.4lf", (double) solo_count[id] / nreps, pval ) ;
            // Make note of the best model
            if (modnum == 0) {
               best_npred = 1 ;
               best_preds[0] = ind_index[i] ;
               }
            goto RANSAC_PRINTED ;
            }
         }

      for (i=0 ; i<n_indicators-1 ; i++) {
         for (j=i+1 ; j<n_indicators ; j++) {
            if (m++ == id) {
               fprintf ( fp_log , "\n\n%15s %10.4lf", names[ind_index[i]], original_crits[id] ) ;
               if (nreps > 1)
                  fprintf ( fp_log , " %10.4lf %10.4lf", (double) solo_count[id] / nreps, pval ) ;
               fprintf ( fp_log , "\n%15s", names[ind_index[j]] ) ;
               // Make note of the best model
               if (modnum == 0) {
                  best_npred = 2 ;
                  best_preds[0] = ind_index[i] ;
                  best_preds[1] = ind_index[j] ;
                  }
               goto RANSAC_PRINTED ;
               }
            }
         }

      for (i=0 ; i<n_indicators-2 ; i++) {
         for (j=i+1 ; j<n_indicators-1 ; j++) {
            for (k=j+1 ; k<n_indicators ; k++) {
               if (m++ == id) {
                  fprintf ( fp_log , "\n\n%15s %10.4lf", names[ind_index[i]], original_crits[id] ) ;
                  if (nreps > 1)
                     fprintf ( fp_log , " %10.4lf %10.4lf", (double) solo_count[id] / nreps, pval ) ;
                  fprintf ( fp_log , "\n%15s", names[ind_index[j]] ) ;
                  fprintf ( fp_log , "\n%15s", names[ind_index[k]] ) ;
                  // Make note of the best model
                  if (modnum == 0) {
                     best_npred = 3 ;
                     best_preds[0] = ind_index[i] ;
                     best_preds[1] = ind_index[j] ;
                     best_preds[2] = ind_index[k] ;
                     }
                  goto RANSAC_PRINTED ;
                  }
               }
            }
         }
      RANSAC_PRINTED: ;
      } // For modnum



/*
-----------------------------------------------------------------------------------

   Retrain the best model and print its specs
   Also write the probabilities to disk, including 'date' if it is first variable

-----------------------------------------------------------------------------------
*/

   if (best_npred) {
      for (i=0 ; i<ncases ; i++)
         target_work[i] = data[i*nvars+target_index] ;

      best_crit = do_ransac ( ncases , sample_size , floor , noise_frac , termination ,
                              best_npred , best_preds , nvars , data , target_work , flags , model_work , probs , predictions , dwork1 , dwork2 ) ;

      if (floor >= 0.0)    // If profit factor, criterion was its reciprocal because we minimize
         best_crit = 1.0 / best_crit ;

      fprintf ( fp_log , "\n\nCriterion for best model = %.5lf", best_crit ) ;

      nterms = best_npred + best_npred * (best_npred+1) / 2 ; // Linear + quadratic
      k1 = 0 ;  // These will index the cross products
      k2 = 1 ;
      for (k=0 ; k<nterms ; k++) {
         if (k < best_npred)         // Linear terms
            fprintf ( fp_log, "\n  %14.6lf  %s", model_work[k], names[best_preds[k]] ) ;
         else if (k < 2*best_npred)  // Squared terms
            fprintf ( fp_log, "\n  %14.6lf  %s Squared", model_work[k], names[best_preds[k-best_npred]] ) ;
         else {                      // Cross products
            fprintf ( fp_log, "\n  %14.6lf  %s * %s", model_work[k], names[best_preds[k1]], names[best_preds[k2]] ) ;
            ++k2 ;
            if (k2 == best_npred) {
               ++k1 ;
               k2 = k1 + 1 ;
               }
            }
         }
      fprintf( fp_log, "\n  %14.6lf  CONSTANT", model_work[nterms]) ;

/*
   Write probability file
*/

      if (noise_frac > 0.0) {
         if (fopen_s ( &fp , "PROB.TXT" , "wt" )) {
            printf ( "\nERROR... Unable to open probability file PROB.TXT for writing." ) ;
            free_data ( nvars , names , data ) ;  // Frees memory allocated by readfile() (names and data)
            goto FINISH ;
            }

         // Rescale 0-100
         dummy = probs[0] ;
         for (i=1 ; i<ncases ; i++) {
            if (probs[i] > dummy)
               dummy = probs[i] ;
            }
         for (i=0 ; i<ncases ; i++)
            probs[i] *= 100.0 / dummy ;

         if (! strcmp ( names[0] , "DATE" )) {
            fprintf ( fp , "DATE PROB" ) ;
            for (i=0 ; i<ncases ; i++)
               fprintf ( fp , "\n%8d %.6lf", (int) data[i*nvars], probs[i] ) ;
            }

         else {
            fprintf ( fp , "PROB" ) ;
            for (i=0 ; i<ncases ; i++)
               fprintf ( fp , "\n%.6lf", probs[i] ) ;
            }
         fclose ( fp ) ;
         }
      }

   free_data ( nvars , names , data ) ;  // Frees memory allocated by readfile() (names and data)

FINISH:

   if (fp_log != NULL)
      fclose ( fp_log ) ;

   if (ind_index != NULL)
      FREE ( ind_index ) ;

   if (target_work != NULL)
      FREE ( target_work ) ;

   if (flags != NULL)
      FREE ( flags ) ;

   if (probs != NULL)
      FREE ( probs ) ;

   if (model_work != NULL)
      FREE ( model_work ) ;

   if (solo_count != NULL)
      FREE ( solo_count ) ;

   if (unbiased_count != NULL)
      FREE ( unbiased_count ) ;

   if (sort_indices != NULL)
      FREE ( sort_indices ) ;

   if (predictions != NULL)
      FREE ( predictions ) ;

   if (dwork1 != NULL)
      FREE ( dwork1 ) ;

   if (dwork2 != NULL)
      FREE ( dwork2 ) ;

   if (crits != NULL)
      FREE ( crits ) ;

   if (original_crits != NULL)
      FREE ( original_crits ) ;

   MEMCLOSE () ;

   DeleteCriticalSection ( &mem64_critsec ) ;  // Needed by MEM64.cpp to be thread-safe!

   printf ( "\n\nPress any key..." ) ;
   _getch () ;  // Wait for user to press a key

   exit ( 0 ) ;
}
