# Methods — Empirical mode decomposition and Hilbert–Huang analysis

## Empirical mode decomposition

Layer 4 multi-unit activity (MUA) time series were analysed separately for each of the
10 trials × 8 drifting-grating directions (80 recordings in total), each sampled at 500 Hz
(2-ms bins). Each MUA signal was decomposed into intrinsic mode functions (IMFs) by empirical
mode decomposition (EMD; Huang et al., 1998), using the EMD Python toolbox (v0.8.1; Quinn et al.,
2021). To obtain stable decompositions that are robust to mode-mixing, we used iterated masked
EMD (itEMD; Fabus et al., 2021): a masking signal is added during sifting (Deering & Kaiser,
2005) and its frequency is re-estimated iteratively from the amplitude-weighted mean instantaneous
frequency of each mode until convergence. Sifting was limited to a maximum of five IMFs, and the
converged mask (carrier) frequency of each IMF was retained (in Hz) for every recording. Mask
frequencies are summarised per IMF as the median and interquartile range across the 80 recordings.

## Hilbert–Huang transform

The instantaneous phase, frequency, and amplitude of each IMF were obtained from its analytic
signal via the Hilbert transform (Huang et al., 1998). Per-IMF amplitude-weighted Hilbert–Huang
transforms (HHT) were then computed over 128 linearly spaced frequency bins spanning 0–100 Hz.
Trial- and direction-resolved IMF waveforms and HHT spectra were averaged across the 80 recordings
and are reported as the mean ± standard error of the mean (SEM). Because IMFs are not strictly
phase-aligned across recordings, trial-averaged IMF waveforms emphasise the stimulus-locked
(phase-locked) component; the mean instantaneous-amplitude (Hilbert envelope) is additionally
reported as a phase-cancellation-free measure of each mode's amplitude time course.

## Harmonic-relationship tests

To determine whether the IMFs reflect independent oscillations rather than harmonics of a common
fundamental, we applied the harmonic-criteria framework of Fabus et al. (2022). Taking the slowest
mode (IMF-5, ≈2 Hz) as the candidate fundamental, each faster IMF was tested against three criteria,
evaluated over 18 approximately equal-length time segments: (i) an **integer instantaneous-frequency
ratio** with the fundamental (one-sample t-test of the per-segment ratio against its nearest integer;
criterion met when p > 0.05); (ii) a **consistent phase relationship**, quantified by the phase–phase
distance correlation and its associated test (Székely et al., 2007; criterion met when p < 0.05); and
(iii) an **amplitude–frequency (af) product below one**, i.e. the product of the amplitude ratio and
frequency ratio of the two modes (one-sided one-sample t-test against 1; criterion met when p < 0.05).
An IMF pair was classified as harmonically related only when all three criteria were satisfied
simultaneously. The criteria were evaluated for every recording and aggregated across the dataset.

Analyses were performed in Python using the EMD toolbox (v0.8.1; Quinn et al., 2021), NumPy, SciPy,
and pandas.

---

## References

- Deering, R., & Kaiser, J. F. (2005). The use of a masking signal to improve empirical mode
  decomposition. *Proceedings of the IEEE International Conference on Acoustics, Speech, and Signal
  Processing (ICASSP)*, 4, 485–488. https://doi.org/10.1109/ICASSP.2005.1416051
- Fabus, M. S., Quinn, A. J., Warnaby, C. E., & Woolrich, M. W. (2021). Automatic decomposition of
  electrophysiological data into distinct nonsinusoidal oscillatory modes. *Journal of
  Neurophysiology*, 126(5), 1670–1684. https://doi.org/10.1152/jn.00315.2021
- Fabus, M. S., Woolrich, M. W., Warnaby, C. W., & Quinn, A. J. (2022). Understanding harmonic
  structures through instantaneous frequency. *IEEE Open Journal of Signal Processing*, 3, 320–334.
  https://doi.org/10.1109/OJSP.2022.3198012
- Huang, N. E., Shen, Z., Long, S. R., Wu, M. C., Shih, H. H., Zheng, Q., Yen, N.-C., Tung, C. C., &
  Liu, H. H. (1998). The empirical mode decomposition and the Hilbert spectrum for nonlinear and
  non-stationary time series analysis. *Proceedings of the Royal Society A*, 454(1971), 903–995.
  https://doi.org/10.1098/rspa.1998.0193
- Quinn, A. J., Lopes-dos-Santos, V., Dupret, D., Nobre, A. C., & Woolrich, M. W. (2021). EMD:
  Empirical Mode Decomposition and Hilbert–Huang spectral analyses in Python. *Journal of Open
  Source Software*, 6(59), 2977. https://doi.org/10.21105/joss.02977
- Székely, G. J., Rizzo, M. L., & Bakirov, N. K. (2007). Measuring and testing dependence by
  correlation of distances. *The Annals of Statistics*, 35(6), 2769–2794.
  https://doi.org/10.1214/009053607000000505
