# http://en.wikipedia.org/wiki/Equal_temperament
tet12 = [2 ** (i / 12.) for i in range(12)]

# http://en.wikipedia.org/wiki/Pythagorean_tuning
pyth = [1., 256/243., 9/8., 32/27., 81/64., 4/3., 2**.5, 3/2., 128/81., 27/16., 16/9., 243/128.]

# http://en.wikipedia.org/wiki/Quarter-comma_meantone#12-tone_scale
qcmt = [1., 8/5**1.25, 5**.5/2, 4/5**.75, 5/4., 2/5**.25, 2**.5, 5**.25, 8/5., 5**.75/2, 4/5**.5, 5**1.25/4]

# http://en.wikipedia.org/wiki/Five-limit_tuning#Twelve_tone_scale
lim5 = [1., 16/15., 5**.5/2, 6/5., 5/4., 4/3., 2**.5, 3/2., 8/5., 5/3., 4/5**.5, 15/8.]

# http://en.wikipedia.org/wiki/Werckmeister_temperament#Werckmeister_III_.28V.29:_an_additional_temperament_divided_up_through_1.2F4_comma
werck = [1., 2**3.25/9, 9/8., 2**.25, 2**3.5/9, 9/2**2.75, 2**.5, 3/2., 128/81., 2**.75, 3/2**.75, 2**2.5/3]

