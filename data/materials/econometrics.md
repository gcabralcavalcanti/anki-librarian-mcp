# Lecture notes: heteroskedasticity in linear regression

**Setting.** In the linear model \(y = X\beta + u\), ordinary least squares (OLS) gives
\(\hat{\beta} = (X'X)^{-1}X'y\). Unbiasedness needs only exogeneity, \(E[u \mid X] = 0\). The usual formula for the
variance of \(\hat{\beta}\), \(\sigma^2 (X'X)^{-1}\), needs one more assumption: homoskedasticity, a constant error
variance, \(Var(u_i \mid X) = \sigma^2\) for every observation.

**What heteroskedasticity is.** The error variance changes with the regressors. Typical case: in a regression of
household spending on income, spending varies much more among high-income households than among low-income ones.

**What it breaks, and what it does not.**
- OLS stays unbiased and consistent (exogeneity still holds).
- The usual standard errors are wrong, so t-tests and confidence intervals are invalid; in the spending example
  they are usually too small, so we reject the null too often.
- OLS is no longer efficient: the Gauss-Markov theorem needs homoskedasticity, so OLS is not BLUE (best linear
  unbiased estimator) any more.

**How to detect it.**
- Plot the residuals against the fitted values: a funnel shape is the classic sign.
- Breusch-Pagan test: regress the squared residuals on the regressors; under the null of homoskedasticity,
  \(nR^2\) from that auxiliary regression follows a chi-squared distribution with k degrees of freedom.
- White test: same idea, adding squares and cross-products of the regressors, so it also catches non-linear
  forms, at the cost of many degrees of freedom.

**What to do.**
1. Keep OLS and use heteroskedasticity-robust standard errors (White, 1980). The "sandwich" estimator replaces
   \(\sigma^2 X'X\) in the middle by \(\sum_i \hat{u}_i^2 x_i x_i'\). Valid in large samples whatever the form of
   heteroskedasticity. This is the default in applied work.
2. Weighted least squares (WLS): if the form of the variance is known, e.g. \(Var(u_i \mid x_i) = \sigma^2 h(x_i)\),
   divide each observation by \(\sqrt{h(x_i)}\); the transformed model is homoskedastic and WLS is efficient.
   If \(h\) is estimated (feasible GLS), efficiency holds only asymptotically and a wrong \(h\) can hurt.
3. Transform the variable: logs often reduce heteroskedasticity in money variables.

**Questions raised in class.**
- Q: If the coefficients are still unbiased, why care? A: because inference is what we report; a wrong standard
  error turns a noisy estimate into a "significant" one.
- Q: Should robust standard errors always be used? A: in large samples they cost little; in small samples they can
  be biased downward, so small-sample corrections (HC2, HC3) are preferred.
- Open: when exactly does WLS with an estimated variance function beat OLS with robust errors in practice?
