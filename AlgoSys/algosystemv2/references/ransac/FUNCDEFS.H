extern int criteria ( int ncases , int *flags , int sample_size , double floor , double noise_frac ,
                      int termination , int n_pred , int n_indicators , int nvars , int *ind_index ,
                      double *data , double *target , double *coefs , double *probs , double *predictions , double *work1 , double *work2 , double *crits ) ;
double do_ransac ( int ncases , int sample_size , double floor , double noise_frac , int termination , int npred , int *preds ,
                   int ncols , double *data , double *target , int *flags , double *coefs , double *probs , double *predictions , double *work1 , double *work2 ) ;
extern void free_data ( int nvars , char **names , double *data ) ;
extern double evaluate_model ( int ncases , int *flags , int npred , int *preds ,
                               int ncols , double *data , double *target , double *coefs ) ;
extern int fit_model ( int ncases , int *flags , int npred , int *preds ,
                       int ncols , double *data , double *target , SingularValueDecomp *sptr , double *coefs ) ;
extern void *memalloc ( size_t n ) ;
extern void *memallocX ( size_t n ) ;
extern void memclose () ;
extern void memcloseX () ;
extern void memfree ( void *ptr ) ;
extern void memfreeX ( void *ptr ) ;
extern void *memrealloc ( void *ptr , size_t size ) ;
extern void *memreallocX ( void *ptr , size_t size ) ;
extern void memtext ( char *text ) ;
extern void nomemclose () ;
extern void notext ( char * ) ;
extern void opt_pf ( int n , int min_kept , int flip_sign , double *signal_vals , double *returns ,
                     double *pf_all , double *high_thresh , double *pf_high , double *low_thresh ,
                     double *pf_low , double *work_signal , double *work_return ) ;
extern void predict_model ( int ncases , int npred , int *preds ,
                            int ncols , double *data , double *predictions , double *coefs ) ;
extern void qsortd ( int first , int last , double *data ) ;
extern void qsortds ( int first , int last , double *data , double *slave ) ;
extern void qsortdsi ( int first , int last , double *data , int *slave ) ;
extern void qsorti ( int first , int last , int *data ) ;
void RAND32M_seed ( int iseed ) ;
extern int readfile ( char *name , int *nvars , char ***names , int *ncases , double **data ) ;
extern double spearman ( int n , double *var1 , double *var2 , double *x , double *y ) ;
extern double unifrand () ;
