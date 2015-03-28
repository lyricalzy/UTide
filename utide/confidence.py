"""
Confidence interval calculations for solve().

Includes a strictly private _confidence() function and
a more general ut_linci() function for linearized estimates
of ellipse parameter uncertainties.
"""

from __future__ import absolute_import, division

import numpy as np
import scipy.interpolate as sip

from .periodogram import ut_pdgm


def _confidence(coef, opt, t, e, tin, tgd, uvgd, elor, xraw, xmod, W, m, B,
                  nm, nt, nc, Xu, Yu, Xv, Yv):
    """
    This confidence interval calculation does not correspond
    to a single ut_ matlab function, but is based on code
    in ut_solv1 starting from the line

    '%% spectral power (Puu, Pvv, Puv) of residual'.

    It returns its first argument, the coef dictionary,
    with additional entries.
    """

    # Confidence Intervals.
    print('conf. int vls... ')

    if not opt['white']:
        # Band-averaged (ba) spectral densities.
        if opt['equi']:
            if np.sum(tgd) > np.sum(uvgd):
                # efill = np.interp1(t, e, tin(tgd))
                # efill = np.interp(t, e, tin[tgd])
                eTemp = sip.interp1d(t, e)
                efill = eTemp(tin[tgd])
                # Fill start&/end nans w/ nearest good.
                if np.any(np.isnan(efill)):
                    ind = np.where(np.isnan(efill))[0]
                    # ind2 = ind(ind<find(~isnan(efill),1,'first'))
                    ind2 = ind[ind < np.where(~np.isnan(efill), 1, 'first')]
                    efill[ind2] = efill[np.max(ind2) + 1]
                    ind2 = ind[ind > np.where(~np.isnan(efill), 1, 'last')]
                    efill[ind2] = efill[np.min(ind2) - 1]

                ba = ut_pdgm(tin[tgd], efill, coef['aux']['frq'], 1, 0)
            else:
                ba = ut_pdgm(tin[tgd], e, coef['aux']['frq'], 1, 0)

        else:
            ba = ut_pdgm(t, e, coef['aux']['frq'], 0, opt['lsfrqosmp'])

        # import pdb; pdb.set_trace()
        # power [ (e units)^2 ] from spectral density [ (e units)^2 / cph ]
        df = 1 / (elor * 24)
        ba['Puu'] = ba['Puu'] * df

        if opt['twodim']:
            ba['Pvv'] = ba['Pvv'] * df
            ba['Puv'] = ba['Puv'] * df

        # Assign band-avg power values to NR & R freqs.
        Puu = np.zeros(coef['aux']['frq'].shape)
        if opt['twodim']:
            Pvv = np.zeros(coef['aux']['frq'].shape)
            Puv = np.zeros(coef['aux']['frq'].shape)
            # This was creating a copy of Puu and not a new array, so Puu was
            # getting overridden
            # Pvv = Puu
            # Puv = Pvv

        # import pdb; pdb.set_trace()
        for i in range(ba['Puu'].shape[0]):

            ind = np.logical_and(coef['aux']['frq'] >= ba['fbnd'][i, 0],
                                 coef['aux']['frq'] <= ba['fbnd'][i, 1])
            ind = np.where(ind[0])
            Puu[ind] = ba['Puu'][i]

            if opt['twodim']:
                Pvv[ind] = ba['Pvv'][i]
                Puv[ind] = ba['Puv'][i]

        # import pdb; pdb.set_trace()
    # varMSM = real((ctranspose(xraw)*W*xraw -
    #                ctranspose(m)*ctranspose(B)*W*xraw)/(nt-nm))
    # varMSM = np.real((np.conj(xraw).T * W * xraw -
    #                  np.conj(m).T[:,None] * np.conj(B).T * W * xraw)/(nt-nm))

    varMSM = np.real((np.dot(np.conj(xraw[:, None]).T * W, xraw[:, None]) -
                      np.dot(np.dot(np.conj(m[:, None]).T, np.conj(B).T) * W,
                             xraw[:, None]))/(nt-nm))

    # gamC = inv(ctranspose(B)*W*B)*varMSM
    gamC = np.linalg.inv(np.dot(np.conj(B).T * W, B)) * varMSM
    # gamP = inv(transpose(B)*W*B)*((transpose(xraw)*W*xraw -
    #            transpose(m)*transpose(B)*W*xraw)/(nt-nm))
    # gamP = np.dot(np.linalg.inv(np.dot(B.T * W, B)),
    #               ((xraw.T * W * xraw - m.T[:,None] * B.T * W *
    #                xraw) / (nt-nm)))

    gamP = (np.linalg.inv(np.dot(B.T * W, B)) *
            (np.dot(xraw[:, None].T * W, xraw[:, None]) -
             np.dot(np.dot(m[:, None].T, B.T) * W, xraw[:, None])) / (nt-nm))

    Gall = gamC + gamP
    Hall = gamC - gamP

    coef['g_ci'] = np.nan*np.ones(coef['g'].shape)
    # import pdb; pdb.set_trace()
    if opt['twodim']:
        # FIXME: change to np.ones_like.
        coef['Lsmaj_ci'] = np.nan * np.ones(coef['g'].shape)
        coef['Lsmin_ci'] = np.nan * np.ones(coef['g'].shape)
        coef['theta_ci'] = np.nan * np.ones(coef['g'].shape)
        # same issue with copying
        # coef['Lsmaj_ci']= coef['g_ci']
        # coef['Lsmin_ci']= coef['g_ci']
        # coef['theta_ci']= coef['g_ci']
        varcov_mCw = np.nan*np.ones((nc, 4, 4))
    else:
        coef['A_ci'] = np.nan*np.ones(coef['g'].shape)
        # coef['A_ci'] = coef['g_ci']
        varcov_mCw = np.nan * np.ones((nc, 2, 2))

    if not opt['white']:
        varcov_mCc = np.copy(varcov_mCw)
        # varcov_mCc = varcov_mCw

    # for c=1:nc
    for c in np.arange(nc):
        # G = [Gall(c,c) Gall(c,c+nc); Gall(c+nc,c) Gall(c+nc,c+nc);];
        G = np.array([[Gall[c, c], Gall[c, c+nc]],
                      [Gall[c+nc, c], Gall[c+nc, c+nc]]])
        H = np.array([[Hall[c, c], Hall[c, c+nc]],
                      [Hall[c+nc, c], Hall[c+nc, c+nc]]])
        # H = [Hall(c,c) Hall(c,c+nc); Hall(c+nc,c) Hall(c+nc,c+nc);];
        varXu = np.real(G[0, 0] + G[1, 1] + 2 * G[0, 1]) / 2
        varYu = np.real(H[0, 0] + H[1, 1] - 2 * H[0, 1]) / 2

        if opt['twodim']:
            varXv = np.real(H[0, 0] + H[1, 1] + 2 * H[0, 1]) / 2
            varYv = np.real(G[0, 0] + G[1, 1] - 2 * G[0, 1]) / 2
            # varXv = real(H(1,1)+H(2,2)+2*H(1,2))/2;
            # varYv = real(G(1,1)+G(2,2)-2*G(1,2))/2;

        if opt['linci']:  # Linearized.
            if not opt['twodim']:
                varcov_mCw[c, :, :] = np.diag(np.array([varXu, varYu]))
                if not opt['white']:
                    den = varXu + varYu
                    varXu = Puu[c]*varXu/den
                    varYu = Puu[c]*varYu/den
                    varcov_mCc[c, :, :] = np.diag(np.array([varXu, varYu]))
                sig1, sig2 = ut_linci(Xu[c], Yu[c], np.sqrt(varXu),
                                      np.sqrt(varYu))
                coef['A_ci'][c] = 1.96*sig1
                coef['g_ci'][c] = 1.96*sig2
            else:
                varcov_mCw[c, :, :] = np.diag(np.array([varXu, varYu,
                                                        varXv, varYv]))
                if not opt['white']:
                    den = varXv + varYv
                    varXv = Pvv[c] * varXv / den
                    varYv = Pvv[c] * varYv / den
                    varcov_mCc[c, :, :] = np.diag(np.array([varXu, varYu,
                                                            varXv, varYv]))
                sig1, sig2 = ut_linci(Xu[c] + 1j * Xv[c], Yu[c] + 1j * Yv[c],
                                      np.sqrt(varXu) + 1j * np.sqrt(varXv),
                                      np.sqrt(varYu) + 1j * np.sqrt(varYv))
                coef['Lsmaj_ci'][c] = 1.96*np.real(sig1)
                coef['Lsmin_ci'][c] = 1.96*np.imag(sig1)
                coef['g_ci'][c] = 1.96*np.real(sig2)
                coef['theta_ci'][c] = 1.96*np.imag(sig2)
                # import pdb; pdb.set_trace()

        else:  # TODO: Monte Carlo.
            pass

    return coef


def ut_linci(X, Y, sigX, sigY):
    # UT_LINCI()
    # current ellipse parameter uncertainties from cosine/sine coefficient
    # uncertainties, by linearized relations w/ correlations presumed zero
    # inputs: (two-dim case complex, one-dim case real)
    # X = Xu + i*Xv
    # Y = Yu + i*Yv
    # for Xu =real(X) = u cosine coeff; Yu =real(Y) = u sine coeff
    # Xv =imag(X) = v cosine coeff; Yv =imag(Y) = v sine coeff
    # sigX = sigXu + i*sigXv
    # sigY = sigYu + i*sigYv
    # for sigXu =real(sigX) =stddev(Xu); sigYu =real(sigY) =stddev(Yu)
    # sigXv =imag(sigX) =stddev(Xv); sigYv =imag(sigY) =stddev(Yv)
    # outputs:
    # two-dim case, complex
    # sig1 = sig_Lsmaj +1i*sig_Lsmin [same units as inputs]
    # sig2 = sig_g + 1i*sig_theta [degrees]
    # one-dim case, real
    # sig1 = sig_A [same units as inputs]
    # sig2 = sig_g [degrees]
    # UTide v1p0 9/2011 d.codiga@gso.uri.edu
    # (adapted from errell.m of t_tide, Pawlowicz et al 2002)

    X = np.array([X])
    Y = np.array([Y])
    sigX = np.array([sigX])
    sigY = np.array([sigY])
    Xu = np.real(X[:])
    sigXu = np.real(sigX)
    Yu = np.real(Y[:])
    sigYu = np.real(sigY)

    Xv = np.imag(X[:])
    sigXv = np.imag(sigX[:])
    Yv = np.imag(Y[:])
    sigYv = np.imag(sigY[:])

    rp = 0.5 * np.sqrt((Xu+Yv)**2 + (Xv-Yu)**2)
    rm = 0.5 * np.sqrt((Xu-Yv)**2 + (Xv+Yu)**2)
    sigXu2 = sigXu**2
    sigYu2 = sigYu**2
    sigXv2 = sigXv**2
    sigYv2 = sigYv**2

    ex = (Xu+Yv) / rp
    fx = (Xu-Yv) / rm
    gx = (Yu-Xv) / rp
    hx = (Yu+Xv) / rm

    # major axis
    dXu2 = (0.25*(ex+fx))**2
    dYu2 = (0.25*(gx+hx))**2
    dXv2 = (0.25*(hx-gx))**2
    dYv2 = (0.25*(ex-fx))**2
    sig1 = np.sqrt(dXu2 * sigXu2 + dYu2 * sigYu2 +
                   dXv2 * sigXv2 + dYv2 * sigYv2)

    # phase
    rn = 2 * (Xu * Yu + Xv * Yv)
    rd = Xu**2 - Yu**2 + Xv**2 - Yv**2
    den = rn**2 + rd**2
    dXu2 = ((rd*Yu - rn*Xu) / den)**2
    dYu2 = ((rd*Xu + rn*Yu) / den)**2
    dXv2 = ((rd*Yv - rn*Xv) / den)**2
    dYv2 = ((rd*Xv + rn*Yv) / den)**2
    sig2 = (180/np.pi) * np.sqrt(dXu2 * sigXu2 + dYu2 * sigYu2 +
                                 dXv2 * sigXv2 + dYv2 * sigYv2)

    # if ~isreal(X)
    if not np.isreal(X):
        # Minor axis.
        dXu2 = (0.25 * (ex-fx))**2
        dYu2 = (0.25 * (gx-hx))**2
        dXv2 = (0.25 * (hx+gx))**2
        dYv2 = (0.25 * (ex+fx))**2
        sig1 = sig1 + 1j*np.sqrt(dXu2 * sigXu2 + dYu2 * sigYu2 +
                                 dXv2 * sigXv2 + dYv2 * sigYv2)

        # Orientation.
        rn = 2.0 * (Xu * Xv + Yu * Yv)
        rd = Xu**2 + Yu**2 - (Xv**2 + Yv**2)
        den = rn**2 + rd**2
        dXu2 = ((rd*Xv - rn*Xu) / den)**2
        dYu2 = ((rd*Yv - rn*Yu) / den)**2
        dXv2 = ((rd*Xu + rn*Xv) / den)**2
        dYv2 = ((rd*Yu + rn*Yv) / den)**2
        sig2 = sig2 + 1j*(180/np.pi) * np.sqrt(dXu2 * sigXu2 + dYu2 * sigYu2 +
                                               dXv2 * sigXv2 + dYv2 * sigYv2)

    return sig1, sig2

