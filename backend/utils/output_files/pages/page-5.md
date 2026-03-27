# Page 5

797 Rafael Bustamante-Alvarez et al. Water Supply Leak Detection Based...

• Processing section: The audio data is processed using a computer programme that implements the necessary algorithms for its analysis, graphing it in time and frequency using the Fast Fourier Transform (FFT), digital filters, audio compression, among others.

• Audio playback section: The signal leaving the converter has a settling time that is the same length as the sampling period, and features an internal zero-order sample-and-hold circuit that prevents glitch in the converter's output level change. Then, once the signal exits the converter, it enters a reconstructor filter that removes the harmonics that give the signal a stepped effect at the output of the analogue digital converter. Then, the signal is amplified to be sent to a loudspeaker.

## The Fast Fourier Transform

This algorithm makes it possible to represent in frequency a digitised signal made up of a set of data representing the original signal. To plot the frequency spectrum of the noise signal, the modulus of the fast transform of the signal squared and divided by the number of samples of the processed signal, measured in Watts/Hertz, which is the unit of spectral power density, is calculated. An example of the application of the FFT for an N=4 signal is shown in Fig. 3 below.

## Figure 3. Schematic of the FFT for blocks of N=4

Table I. Reverse bits Order of signal samples before reverse bit

Order of FFT inputs with reverse bit 00 (0) 00 (0) 01 (1) 10 (2) 10 (2) 01 (1) 11 (3) 11 (3)

## Fig. 4 shows the entries obtained in Table I.

## Figure 4. Butterfly diagram for N=4

## Nanotechnology Perceptions Vol. 20 No. S9 (2024)
