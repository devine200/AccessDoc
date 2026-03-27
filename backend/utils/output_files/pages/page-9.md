# Page 9

801 Rafael Bustamante-Alvarez et al. Water Supply Leak Detection Based...

Using a program developed in Matlab, the audio signals obtained from the Line and Corporation sections are processed. The recorded sounds were captured with a sampling frequency of 44.1Khz and 16 bits of resolution by means of a probe. For the elaboration of the programme it has been considered that the signal has to be filtered by means of a digital IIR Chebyshev 2 filter to filter the signal by means of a band pass filter between 1000Hz and 5000Hz which is the frequency band where the water leakage sounds occur. Additional features of the filter have already been described in the previous section of the system simulation. Fig. 11 and Fig.12 show the graphs of the audio signals of the water leaks.

## Figure 11. Audio signal in Corporation Section

The Fast Fourier Transform (FFT) function is then applied to the filtered signal, resulting in a plot of the signal's Spectral Power Density (w/Hz) versus frequency (Hertz). To detect the presence of noise, a threshold of 0.2W/Hz has been set in the frequency band between 1000Hz and 5000Hz.

## Figure 12. Audio signal in the Line Section

## Nanotechnology Perceptions Vol. 20 No. S9 (2024)
