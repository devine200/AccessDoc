# Page 8

Water Supply Leak Detection Based…  Rafael Bustamante-Alvarez et al. 800

and seventh blocks are part of the processing section, where the sixth block is called uniform decoder (peak=1 and Bits=16), the seventh block is a digital band pass IIR (Infinite Impulse Response) filter that filters the water leakage noise signal between 1000Hz and 5000Hz. The type of filter is Chebyshev type 2 with number of coefficients 13, ripple (rs=0.1), normalised frequencies (1000 / 22050, 5000 / 22050) generating the coefficients shown in Fig. 8.

## Figure 8. Resultant filter coefficients

In this filter block the numerator and denominator are only the values of A and B respectively. Then in the playback section, the eighth block which is gain2 (k=1e5) and finally the ninth block called Spectrum Analyzer whose parameters are shown in Fig 9.

Figure 9. Simulation of the process of capturing the sound of water leakage for detection

Fig. 10 shows the noise signal spectrum on the analyser. It can be seen that the spectrum is limited between 1000Hz and 5000Hz, the spectral density exceeds 0.02W/Hz which is the threshold to indicate if there is noise due to water leakage. Also, the different parameters of the analyser are presented.

## Figure 10. Spectrum and analyser parameters

## Signal analysis process

The present study involves collecting the necessary information for the frequency representation of the water leakage sounds at the points of the water pipes with and without water leakage.

## Nanotechnology Perceptions Vol. 20 No. S9 (2024)
