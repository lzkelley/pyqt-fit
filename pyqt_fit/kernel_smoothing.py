"""
:Author: Pierre Barbier de Reuille <pierre.barbierdereuille@gmail.com>

Module implementing non-parametric regressions using kernel smoothing methods.
"""

from scipy import stats
from scipy.special import gamma
from scipy.linalg import sqrtm, solve
import scipy
import numpy as np

import cyth
import cy_local_linear

from kde import scotts_bandwidth
from kernels import normal_kernel

class SpatialAverage(object):
    r"""
    Perform a Nadaraya-Watson regression on the data (i.e. also called local-constant regression) using a gaussian kernel.

    The Nadaraya-Watson estimate is given by:

    .. math::

        f_n(x) \triangleq \frac{\sum_i K\left(\frac{x-X_i}{h}\right) Y_i}{\sum_i K\left(\frac{x-X_i}{h}\right)}

    Where :math:`K(x)` is the kernel and must be such that :math:`E(K(x)) = 0` and :math:`h` is the bandwidth of the
    method.

    :param ndarray xdata: Explaining variables (at most 2D array)
    :param ndarray ydata: Explained variables (should be 1D array)

    :type  cov: ndarray or callable
    :param cov: If an ndarray, it should be a 2D array giving the matrix of covariance of the gaussian kernel.
        Otherwise, it should be a function ``cov(xdata, ydata)`` returning the covariance matrix.

    """

    def __init__(self, xdata, ydata, cov = scotts_bandwidth):
        self.xdata = np.atleast_2d(xdata)
        self.ydata = ydata

        self._bw = None
        self._covariance = None
        self._inv_cov = None

        self.covariance = cov

        self.d, self.n = self.xdata.shape
        self.correction = 1.

    @property
    def bandwidth(self):
        """
        Bandwidth of the kernel. It cannot be set directly, but rather should be set via the covariance attribute.
        """
        if self._bw is None and self._covariance is not None:
            self._bw = np.real(sqrtm(self._covariance))
        return self._bw

    @property
    def covariance(self):
        """
        Covariance of the gaussian kernel.
        Can be set either as a fixed value or using a bandwith calculator, that is a function
        of signature ``w(xdata, ydata)`` that returns a 2D matrix for the covariance of the kernel.
        """
        return self._covariance

    @covariance.setter
    def covariance(self, cov):
        if callable(cov):
            _cov = np.atleast_2d(bw(self.xdata, self.ydata))
        else:
            _cov = np.atleast_2d(bw)
        self._bw = None
        self._covariance = _cov
        self._inv_cov = scipy.linalg.inv(_cov)


    def evaluate(self, points, result = None):
        """
        Evaluate the spatial averaging on a set of points

        :param ndarray points: Points to evaluate the averaging on
        :param ndarray result: If provided, the result will be put in this array
        """
        points = np.atleast_2d(points).astype(self.xdata.dtype)
        #norm = self.kde(points)
        d, m = points.shape
        if result is None:
            result = np.zeros((m,), points.dtype)
        norm = np.zeros((m,), points.dtype)

        # iterate on the internal points
        for i,ci in np.broadcast(xrange(self.n), xrange(self._correction.shape[0])):
            diff = np.dot(self._correction[ci], self.xdata[:,i,np.newaxis] - points)
            tdiff = np.dot(self._inv_cov, diff)
            energy = np.exp(-np.sum(diff*tdiff,axis=0)/2.0)
            result += self.ydata[i]*energy
            norm += energy

        result[norm>1e-50] /= norm[norm>1e-50]

        return result

    def __call__(self, *args, **kwords):
        """
        This method is an alias for :py:meth:`SpatialAverage.evaluate`
        """
        return self.evaluate(*args, **kwords)

    @property
    def correction(self):
        """
        The correction coefficient allows to change the width of the kernel depending on the point considered.
        It can be either a constant (to correct globaly the kernel width), or a 1D array of same size as the input.
        """
        return self._correction

    @correction.setter
    def correction(self, value):
        self._correction = np.atleast_1d(value)

    def set_density_correction(self):
        """
        Add a correction coefficient depending on the density of the input
        """
        kde = stats.gaussian_kde(xdata)
        dens = kde(xdata)
        dm = dens.max()
        dens[dens < 1e-50] = dm
        self._correction = dm/dens

class LocalLinearKernel1D(object):
    r"""
    Perform a local-linear regression using a gaussian kernel.

    The local constant regression is the function that minimises, for each position:

    .. math::

        f_n(x) \triangleq \argmin_{a_0\in\mathbb{R}} \sum_i K\left(\frac{x-X_i}{h}\right)\left(Y_i - a_0 -
        a_1(x-X_i)\right)^2

    Where :math:`K(x)` is the kernel and must be such that :math:`E(K(x)) = 0` and :math:`h` is the bandwidth of the
    method.

    :param ndarray xdata: Explaining variables (at most 2D array)
    :param ndarray ydata: Explained variables (should be 1D array)

    :type  cov: float or callable
    :param cov: If an float, it should be a variance of the gaussian kernel.
        Otherwise, it should be a function ``cov(xdata, ydata)`` returning the variance.

    """
    def __init__(self, xdata, ydata, cov = scotts_bandwidth):
        self.xdata = np.atleast_1d(xdata)
        self.ydata = np.atleast_1d(ydata)
        self.n = xdata.shape[0]

        self._bw = None
        self._covariance = None

        self.covariance = cov

    @property
    def bandwidth(self):
        """
        Bandwidth of the kernel.
        """
        return self._bw


    @property
    def covariance(self):
        """
        Covariance of the gaussian kernel.
        Can be set either as a fixed value or using a bandwith calculator, that is a function
        of signature ``w(xdata, ydata)`` that returns a single value.

        .. note::

            A ndarray with a single value will be converted to a floating point value.
        """
        return self._covariance

    @covariance.setter
    def covariance(self, cov):
        if callable(cov):
            _cov = float(cov(self.xdata, self.ydata))
        else:
            _cov = float(cov)
        self._covariance = _cov
        self._bw = np.sqrt(_cov)

    def evaluate(self, points, output=None):
        """
        Evaluate the spatial averaging on a set of points

        :param ndarray points: Points to evaluate the averaging on
        :param ndarray result: If provided, the result will be put in this array
        """
        li2, output = cy_local_linear.cy_local_linear_1d(self._bw, self.xdata, self.ydata, points, output)
        self.li2 = li2
        return output
        #points = np.atleast_1d(points).astype(self.xdata.dtype)
        #m = points.shape[0]
        #x0 = points - self.xdata[:,np.newaxis]
        #x02 = x0*x0
        #wi = np.exp(-self.inv_cov*x02/2.0)
        #X = np.sum(wi*x0, axis=0)
        #X2 = np.sum(wi*x02, axis=0)
        #wy = wi*self.ydata[:,np.newaxis]
        #Y = np.sum(wy, axis=0)
        #Y2 = np.sum(wy*x0, axis=0)
        #W = np.sum(wi, axis=0)
        #return np.divide(X2*Y-Y2*X, W*X2-X*X, output)

    def __call__(self, *args, **kwords):
        """
        This method is an alias for :py:meth:`LocalLinearKernel1D.evaluate`
        """
        return self.evaluate(*args, **kwords)

class LocalPolynomialKernel1D(object):
    r"""
    Perform a local-polynomial regression using a user-provided kernel (Gaussian by default).

    The local constant regression is the function that minimises, for each position:

    .. math::

        f_n(x) \triangleq \argmin_{a_0\in\mathbb{R}} \sum_i K\left(\frac{x-X_i}{h}\right)\left(Y_i - a_0 -
        a_1(x-X_i) - \ldots - a_q \frac{(x-X_i)^q}{q!}\right)^2

    Where :math:`K(x)` is the kernel such that :math:`E(K(x)) = 0`, :math:`q`
    is the order of the fitted polynomial  and :math:`h` is the bandwidth of
    the method. It is also recommended to have :math:`\int_\mathbb{R} x^2K(x)dx
    = 1`, (i.e. variance of the kernel is 1) or the effective bandwidth will be
    scaled by the square-root of this integral (i.e. the standard deviation of
    the kernel).

    :param ndarray xdata: Explaining variables (at most 2D array)
    :param ndarray ydata: Explained variables (should be 1D array)
    :param int q: Order of the polynomial to fit. **Default:** 3
    :param callable kernel: Kernel to use for the weights. Call is
        ``kernel(points)`` and should return an array of values the same size
        as ``points``. **Default:** ``scipy.stats.norm(0,1).pdf``

    :type  cov: float or callable
    :param cov: If an float, it should be a variance of the gaussian kernel.
        Otherwise, it should be a function ``cov(xdata, ydata)`` returning the variance. **Default:** ``scotts_bandwidth``

    """
    def __init__(self, xdata, ydata, q = 3, cov = scotts_bandwidth, kernel = None):
        self.xdata = np.atleast_1d(xdata)
        self.ydata = np.atleast_1d(ydata)
        if kernel is None:
            kernel = normal_kernel(1)
        self.kernel = kernel
        self.n = xdata.shape[0]
        self.q = q

        self._bw = None
        self._covariance = None

        self.covariance = cov

    @property
    def bandwidth(self):
        """
        Bandwidth of the kernel.
        """
        return self._bw


    @property
    def covariance(self):
        """
        Covariance of the gaussian kernel.
        Can be set either as a fixed value or using a bandwith calculator, that is a function
        of signature ``w(xdata, ydata)`` that returns a single value.

        .. note::

            A ndarray with a single value will be converted to a floating point value.
        """
        return self._covariance

    @covariance.setter
    def covariance(self, cov):
        if callable(cov):
            _cov = float(cov(self.xdata, self.ydata))
        else:
            _cov = float(cov)
        self._covariance = _cov
        self._bw = np.sqrt(_cov)

    def evaluate(self, points, output=None):
        """
        Evaluate the spatial averaging on a set of points

        :param ndarray points: Points to evaluate the averaging on
        :param ndarray result: If provided, the result will be put in this array
        """
        xdata = self.xdata[:,np.newaxis] # make it a column vector
        ydata = self.ydata[:,np.newaxis] # make it a column vector
        q = self.q
        powers = np.arange(0,q+1).reshape((1,q+1)) # This is a line vector
        frac = gamma(powers+1) # gamma(x+1) = x! if x is integer
        bw = self.bandwidth
        kernel = self.kernel
        if output is None:
            output = np.empty(points.shape, dtype=float)
        for i,p in enumerate(points):
            dX = (xdata - p)
            Wx = kernel(dX/bw)
            Xx = np.power(dX, powers) / frac
            WxXx = Wx*Xx
            XWX = np.dot(Xx.T, WxXx)
            Lx = solve(XWX, WxXx.T)[0]
            output[i] = np.dot(Lx, ydata)
        return output

    def __call__(self, *args, **kwords):
        """
        This method is an alias for :py:meth:`LocalLinearKernel1D.evaluate`
        """
        return self.evaluate(*args, **kwords)

def designMatrixSize(dim, deg, factors = False):
    """
    Compute the size of the design matrix for a n-D problem of order d. Can also
    compute the Taylors factors (i.e. the factors that would be applied for the
    taylor decomposition)

    :param int dim: Dimension of the problem
    :param int deg: Degree of the fitting polynomial
    :param bool factors: If true, the output includes the Taylor factors

    :returns: The number of columns in the design matrix and, if required, a
        ndarray with the taylor coefficients for each column of the design matrix.
    """
    init = 1
    dims = [0] * (dim+1)
    cur = init
    prev = 0
    if factors:
        fcts = [1]
    fact = 1
    for i in xrange(deg):
        diff = cur - prev
        prev = cur
        old_dims = list(dims)
        fact *= (i+1)
        for j in xrange(dim):
            dp = diff - old_dims[j]
            cur += dp
            dims[j+1] = dims[j]+dp
        if factors:
            fcts += [fact]*(cur-prev)
    if factors:
        return cur, np.array(fcts)
    return cur

def designMatrix(x, deg, factors = None, out = None):
    """
    Creates the design matrix for polynomial fitting using the points x.

    :param ndarray x: Points to create the design matrix. Shape must be (D,N)
        or (N,), where D is the dimension of the problem, 1 if not there.

    :param int deg: Degree of the fitting polynomial

    :param ndarray factors: Scaling factor for the columns of the design
        matrix. The shape should be (M,) or (M,1), where M is the number of columns
        of the output. This value can be obtained using the :py:func:`designMatrixSize` function.

    :returns: The design matrix as a (M,N) matrix.
    """
    x = np.atleast_2d(x)
    dim = x.shape[0]
    if out is None:
        s = designMatrixSize(dim, deg)
        out = np.empty((s, x.shape[1]), dtype=x.dtype)
    dims = [0]*(dim+1)
    out[0,:] = 1
    cur = 1
    for i in xrange(deg):
        old_dims = list(dims)
        prev = cur
        for j in xrange(x.shape[0]):
            dims[j] = cur
            for k in xrange(old_dims[j], prev):
                np.multiply(out[k], x[j], out[cur])
                cur += 1
    if factors is not None:
        factors = np.asarray(factors)
        if len(factors.shape) == 1:
            factors = factors[:,np.newaxis]
        out /= factors
    return out


class LocalPolynomialKernel(object):
    r"""
    Perform a local-polynomial regression in N-D using a user-provided kernel (Gaussian by default).

    The local constant regression is the function that minimises, for each position:

    .. math::

        f_n(x) \triangleq \argmin_{a_0\in\mathbb{R}} \sum_i K\left(\frac{x-X_i}{h}\right)\left(Y_i - a_0 - \mathcal{P}_q(X_i-x)\right)^2

    Where :math:`K(x)` is the kernel such that :math:`E(K(x)) = 0`, :math:`q`
    is the order of the fitted polynomial, :math:`\mathcal{P}_q(x)` is a
    polynomial of order :math:`d` in :math:`x` and :math:`h` is the bandwidth of
    the method.

    The polynomial :math:`\mathcal{P}_q(x)` is of the form:

    .. math::

        \mathcal{F}_d(k) = \left\{ \n \in \mathbb{N}^d \middle| \sum_{i=1}^d n_i = k \right\}

        \mathcal{P}_q(x_1,\ldots,x_d) = \sum_{k=1}^q \sum_{\n\in\mathcal{F}_d(k)} a_{k,\n} \prod_{i=1}^d x_i^{n_i}

    For example we have:

    .. math::

        \mathcal{P}_2(x,y) = a_{110} x + a_{101} y + a_{220} x^2 + a_{211} xy + a_{202} y^2

    :param ndarray xdata: Explaining variables (at most 2D array). The shape should be
        (N,D) with D the dimension of the problem and N the number of points.
        For 1D array, the shape can be (N,), in which case it will be converted
        to (N,1) array.
    :param ndarray ydata: Explained variables (should be 1D array). The shape
        must be (N,).
    :param int q: Order of the polynomial to fit. **Default:** 3
    :param callable kernel: Kernel to use for the weights. Call is
        ``kernel(points)`` and should return an array of values the same size
        as ``points``. If ``None``, the kernel will be ``normal_kernel(D)``.

    :type  cov: float or callable
    :param cov: If an float, it should be a variance of the gaussian kernel.
        Otherwise, it should be a function ``cov(xdata, ydata)`` returning the variance. **Default:** ``scotts_bandwidth``

    """
    def __init__(self, xdata, ydata, q = 3, cov = scotts_bandwidth, kernel = None):
        self.xdata = np.atleast_2d(xdata)
        self.ydata = np.atleast_1d(ydata)
        self.d, self.n = xdata.shape
        self.q = q
        if kernel is None:
            kernel = normal_kernel(self.d)
        self.kernel = kernel

        self._bw = None
        self._covariance = None

        self.covariance = cov

    @property
    def bandwidth(self):
        """
        Bandwidth of the kernel.
        """
        return self._bw


    @property
    def covariance(self):
        """
        Covariance of the gaussian kernel.
        Can be set either as a fixed value or using a bandwith calculator, that is a function
        of signature ``w(xdata, ydata)`` that returns a DxD matrix.

        .. note::

            A ndarray with a single value will be converted to a floating point value.
        """
        return self._covariance

    @covariance.setter
    def covariance(self, cov):
        if callable(cov):
            _cov = cov(self.xdata, self.ydata)
        else:
            _cov = np.atleast_2d(cov)
        self._covariance = _cov
        self._bw = np.real(sqrtm(_cov))

    def evaluate(self, points, output=None):
        """
        Evaluate the spatial averaging on a set of points

        :param ndarray points: Points to evaluate the averaging on
        :param ndarray result: If provided, the result will be put in this array
        """
        xdata = self.xdata
        ydata = self.ydata[:,np.newaxis] # make it a column vector
        points = np.atleast_2d(points)
        n = self.n
        q = self.q
        d = self.d
        dm_size, frac = designMatrixSize(d, q, True)
        Xx = np.empty((dm_size, n), dtype=xdata.dtype)
        WxXx = np.empty(Xx.shape, dtype=xdata.dtype)
        XWX = np.empty((dm_size,dm_size), dtype=xdata.dtype)
        inv_bw = scipy.linalg.inv(self.bandwidth)
        kernel = self.kernel
        if output is None:
            output = np.empty((points.shape[1],), dtype=float)
        for i in xrange(points.shape[1]):
            dX = (xdata - points[:,i:i+1])
            Wx = kernel(np.dot(inv_bw, dX))
            designMatrix(dX, q, frac, out = Xx)
            np.multiply(Wx, Xx, WxXx)
            np.dot(Xx, WxXx.T, XWX)
            Lx = solve(XWX, WxXx)[0]
            output[i] = np.dot(Lx, ydata)
        return output

    def __call__(self, *args, **kwords):
        """
        This method is an alias for :py:meth:`LocalLinearKernel1D.evaluate`
        """
        return self.evaluate(*args, **kwords)

