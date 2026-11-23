1. Is hardware log_tile accurate to ~1e-5 absolute for x near 1? If not, should I add a Newton step (y += x*exp(-y) - 1) or a custom SFPU polynomial?
2. Which entry-point form does 0.63 expect: NAMESPACE MAIN or kernel_main()?
