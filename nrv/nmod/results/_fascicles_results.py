"""
NRV-:class:`.fascicle_results` handling.
"""

from ...backend.NRV_Results import sim_results
from ...backend.log_interface import pass_info, rise_warning, rise_error
from ...backend.MCore import MCH
from ...fmod.electrodes import is_FEM_electrode
from ...utils.units import nm, convert, from_nrv_unit, to_nrv_unit
from ...utils.misc import membrane_capacitance_from_model, compute_complex_admitance
import matplotlib.pyplot as plt
import numpy as np


def number_in_str(s: str) -> bool:
    return any(i.isdigit() for i in s)


recognized_axon_types = ["all", "myelinated", "unmyelinated"]


class fascicle_results(sim_results):
    """ """

    def __init__(self, context=None):
        super().__init__(context)

    @property
    def n_ax(self):
        """
        Number of axons in the fascicle
        """
        return len(self.axons_diameter)

    def get_n_ax(self, ax_type: str = "all") -> int:
        """
        Number of myelinated axons in the fascicle
        """
        return len(self.get_axons_key(ax_type))

    def get_axons_key(self, ax_type: str = "all") -> list:
        """ """
        if ax_type not in recognized_axon_types:
            rise_error(
                f"Axon type specified not recognized. Recognized types are: {recognized_axon_types}"
            )
        all_keys = self.keys()
        axon_keys = [i for i in all_keys if ("axon" in i and number_in_str(i))]
        if ax_type != "all":
            if ax_type == "unmyelinated":
                axon_keys = [i for i in axon_keys if self[i].myelinated == False]
            else:
                axon_keys = [i for i in axon_keys if self[i].myelinated == True]
        return axon_keys

    def get_recruited_axons(
        self, ax_type: str = "all", normalize: bool = False
    ) -> int | float:
        """
        Return the number or the ratio of recruited axons in the fascicle

        Parameters
        ----------
        ax_type : str, optional
            type of axon counted,possible options:
             - "all" (default)
             - "unmyelinated"
             - "myelinated"
        normalize : bool, optional
            if False the total number of recruited axons is returned, else the ratio is returned, by default False

        Returns
        -------
        int or float
            number of recruited axons
        """
        axons_keys = self.get_axons_key(ax_type)
        n_recr = 0
        for axon in axons_keys:
            if self[axon].is_recruited():
                n_recr += 1
        if normalize:
            n_recr /= self.get_n_ax(ax_type)
        return n_recr

    def get_recruited_axons_greater_than(
        self, diam: float, ax_type: str = "all", normalize: bool = False
    ) -> float:
        """
        Return the number or the ratio of recruited axons with a diameter greater than `diam` in the fascicle

        Parameters
        ----------
        ax_type : str, optional
            type of axon counted, possible options:
                - "all" (default)
                - "unmyelinated"
                - "myelinated"
        normalize : bool, optional
            if False the total number of recruited axons is returned, else the ratio is returned, by default False

        Returns
        -------
        int or float
            number of recruited axons
        """
        axons_keys = self.get_axons_key(ax_type)
        n_recr = 0
        n_tot = 0
        for axon in axons_keys:
            if self[axon].diameter > diam:
                n_tot += 1
                if self[axon].is_recruited():
                    n_recr += 1
        if normalize:
            n_recr /= n_tot
        return n_recr

    def get_recruited_axons_lesser_than(
        self, diam: float, ax_type: str = "all", normalize: bool = False
    ) -> float:
        """
        Return the number or the ratio of recruited axons with a diameter smaller than `diam` in the fascicle

        Parameters
        ----------
        ax_type : str, optional
            type of axon counted, possible options:
                - "all" (default)
                - "unmyelinated"
                - "myelinated"
        normalize : bool, optional
            if False the total number of recruited axons is returned, else the ratio is returned, by default False

        Returns
        -------
        int or float
            number of recruited axons
        """
        axons_keys = self.get_axons_key(ax_type)
        n_recr = 0
        n_tot = 0
        for axon in axons_keys:
            if self[axon].diameter < diam:
                n_tot += 1
                if self[axon].is_recruited():
                    n_recr += 1
        if normalize:
            n_recr /= n_tot
        return n_recr

    def get_axons(self) -> list:
        axons_keys = self.get_axons_key()
        axon_diam = []
        axon_type = []
        axon_y = []
        axon_z = []
        axon_recruited = []
        for axon in axons_keys:
            axon_recruited.append(self[axon].is_recruited())
            axon_y.append(self[axon].y)
            axon_z.append(self[axon].z)
            axon_diam.append(self[axon].diameter)
            axon_type.append(self[axon].myelinated)
        return (axon_diam, axon_type, axon_y, axon_z, axon_recruited)

    def get_block_summary_axons(
        self, AP_start: float, freq: float = None, t_refractory: float = 1
    ) -> list:
        axons_keys = self.get_axons_key()
        axon_diam = []
        axon_type = []
        axon_y = []
        axon_z = []
        is_blocked = []
        n_onset = []
        for axon in axons_keys:
            self[axon].block_summary(AP_start, freq, t_refractory)

            is_blocked.append(self[axon].is_blocked)
            n_onset.append(self[axon].n_onset)
            axon_y.append(self[axon].y)
            axon_z.append(self[axon].z)
            axon_diam.append(self[axon].diameter)
            axon_type.append(self[axon].myelinated)
        return (axon_diam, axon_type, axon_y, axon_z, is_blocked, n_onset)

    # impeddance related methods
    def get_membrane_conductivity(
        self, x: float = 0, t: float = 0, unit: str = "S/cm**2", mem_th: float = 7 * nm
    ) -> np.array:
        """
        get the membran conductivity of each axon at a position x and a time t

        Parameters
        ----------
        x : float, optional
            x-position in um where to get the conductivity, by default 0
        t : float, optional
            simulation time in ms when to get the conductivity, by default 0
        unit : str, optional
            unit of the returned conductivity see `units`, by default "S/cm**2"
        mem_th : float, optional
            membrane thickness in um, by default 7*nm

        Note
        ----
        depending of the unit parameter this function either return :

            - the surface conductivity in [S]/([m]*[m]): from neuron simulation
            - the conductivity in [S]/[m]:  by multiplying surface conductivity by membrane thickness
        """

        g = []
        a_keys = self.get_axons_key()
        for key in a_keys:
            g_ = self[key].get_membrane_conductivity(x=x, t=t, unit=unit, mem_th=mem_th)
            if g_ is not None:
                g = np.concatenate((g, [g_]))
            else:
                return None
        return g

    def get_membrane_capacitance(
        self, unit: str = "uF/cm**2", mem_th: float = 7 * nm
    ) -> tuple[float]:
        """
        get the membrane capacitance or permitivity of unmyelinated and myelinated axons filling the ner

        Parameters
        ----------
        unit : str, optional
            unit of the returned conductivity see `units`, by default "S/cm**2"
        mem_th : float, optional
            membrane thickness in um, by default 7*nm

        Note
        ----
        depending of the unit parameter this function either return :

            - the surface capacitance in [S]/([m]*[m]): from neuron simulation
            - the permitivity in [S]/[m]:  by multiplying surface conductivity by membrane thickness
        """
        u_c_mem = membrane_capacitance_from_model(self.unmyelinated_param["model"])
        m_c_mem = membrane_capacitance_from_model(self.myelinated_param["model"])

        # Surface capacity in [F]/([m]*[m])
        if "2" in unit:
            return convert(u_c_mem, "S/cm**2", unit), convert(m_c_mem, "S/cm**2", unit)
        # permitivity in [F]/[m]
        else:
            u_c_mem *= from_nrv_unit(mem_th, "cm")
            m_c_mem *= from_nrv_unit(mem_th, "cm")
            return convert(u_c_mem, "S/cm", unit), convert(m_c_mem, "S/cm", unit)

    def get_membrane_complexe_admitance(
        self,
        f: float = 1.0,
        x: float = 0,
        t: float = 0,
        unit: str = "S/m",
        mem_th: float = 7 * nm,
    ) -> np.array:
        """
        get the membran complexe admitance of each axon at a position x and a time t for a given frequency

        Parameters
        ----------
        f : float or np.array, optional
            effective frequency in kHz, by default 1
        x : float, optional
            x-position in um where to get the conductivity, by default 0
        t : float, optional
            simulation time in ms when to get the conductivity, by default 0
        unit : str, optional
            unit of the returned conductivity see `units`, by default "S/cm**2"
        mem_th : float, optional
            membrane thickness in um, by default 7*nm
        """
        u_c, m_c = self.get_membrane_capacitance(mem_th=mem_th)
        eps = (self.axons_type * (m_c - u_c)) + u_c
        g = self.get_membrane_conductivity(x=x, t=t, mem_th=mem_th)
        f_mem = g / (2 * np.pi * eps)

        # in [MHz] as g_mem in [S/cm^{2}] and c_mem [uF/cm^{2}]
        # [MHz] to convert to [kHz]
        f_mem = to_nrv_unit(f_mem, "MHz")

        Y = compute_complex_admitance(f=f, g=g, fc=f_mem)

        if "2" in unit:
            return convert(Y, "S/cm**2", unit)
        # permitivity in [F]/[m]
        else:
            Y *= from_nrv_unit(mem_th, "cm")
            return convert(Y, "S/cm", unit)

    def get_block_summary(
        self,
        AP_start: float,
        freq: float = None,
        t_refractory_m: float = 1,
        t_refractory_um: float = 1,
    ) -> None:
        """
        Get block characteristics (blocked, onset response, number of APs) for each axon of the fascicle

        Parameters
        ----------
        AP_start : float
            timestamp of the test pulse start, in ms.
        freq : float, optional
            Frequency of the stimulation, for KES block, by default None
        t_refractory_m : float, optional
            Axon refractory period for myelinated fibers, by default 1
        t_refractory_um : float, optional
            Axon refractory period for unmyelinated fibers, by default 1
        """
        axons_keys = self.get_axons_key()
        for axon in axons_keys:
            if self[axon].myelinated == True:
                self[axon].block_summary(AP_start, freq, t_refractory_m)
            else:
                self[axon].block_summary(AP_start, freq, t_refractory_um)

    ## Representation methods
    def plot_recruited_fibers(
        self,
        axes: plt.axes,
        contour_color: str = "k",
        myel_color: str = "r",
        unmyel_color: str = "b",
        num: bool = False,
    ) -> None:
        if MCH.do_master_only_work():
            ## plot contour
            axes.add_patch(
                plt.Circle(
                    (self.y_grav_center, self.z_grav_center),
                    self.D / 2,
                    color=contour_color,
                    fill=False,
                    linewidth=2,
                )
            )
            ## plot axons
            axon_diam, axon_type, axon_y, axon_z, axon_recruited = self.get_axons()
            for k, _ in enumerate(axon_diam):
                color = unmyel_color
                if axon_type[k]:
                    color = myel_color
                alpha = 0.1
                if axon_recruited[k]:
                    alpha = 1
                axes.add_patch(
                    plt.Circle(
                        (axon_y[k], axon_z[k]),
                        axon_diam[k] / 2,
                        color=color,
                        fill=True,
                        alpha=alpha,
                    )
                )

            if self.extra_stim is not None:
                self.extra_stim.plot(axes=axes, color="gold", nerve_d=self.D)
            if num:
                for k in range(self.n_ax):
                    axes.text(
                        self.axons_y[k],
                        self.axons_z[k],
                        str(k),
                        horizontalalignment="center",
                        verticalalignment="center",
                    )
            axes.set_xlim(
                (
                    -1.1 * self.D / 2 + self.y_grav_center,
                    1.1 * self.D / 2 + self.y_grav_center,
                )
            )
            axes.set_ylim(
                (
                    -1.1 * self.D / 2 + self.z_grav_center,
                    1.1 * self.D / 2 + self.z_grav_center,
                )
            )

    def plot_block_summary(
        self,
        axes: plt.axes,
        AP_start: float,
        freq: float = None,
        t_refractory: float = 1,
        contour_color: str = "k",
        num: bool = False,
    ) -> None:
        """
        plot the block_summary of the fascicle in the Y-Z plane (transverse section)
        Color code:
        Green: fiber is blocked without any onset
        Blue: fiber is blocked with some onset
        Red: fiber is not blocked but has onset
        Grey: Fiber is nor blocked nor has onset

        A cross-mark on the fiber means block state can't be evaluted (is_blocked returned None)
        Alpha colorfill represents number of onset APs.

        Parameters
        ----------
        axes    : matplotlib.axes
            axes of the figure to display the fascicle
        AP_start : float
            timestamp of the test pulse start, in ms.
        freq : float, optional
            Frequency of the stimulation, for KES block, by default None
        t_refractory : float, optional
            Axon refractory period for myelinated fibers, by default 1
        contour_color   : str
            matplotlib color string applied to the contour. Black by default
        num             : bool
            if True, the index of each axon is displayed on top of the circle
        """

        if MCH.do_master_only_work():
            ## plot contour
            axes.add_patch(
                plt.Circle(
                    (self.y_grav_center, self.z_grav_center),
                    self.D / 2,
                    color=contour_color,
                    fill=False,
                    linewidth=2,
                )
            )
            ## plot axons
            axon_diam, _, axon_y, axon_z, is_blocked, n_onset = (
                self.get_block_summary_axons(
                    AP_start=AP_start, freq=freq, t_refractory=t_refractory
                )
            )
            alpha_g = 1 / np.max(n_onset)

            # cmap = plt.get_cmap('viridis')
            # norm = plt.Normalize(min(n_onset), max(n_onset))
            # line_colors = cmap((n_onset))

            for k, _ in enumerate(axon_diam):
                if is_blocked[k] is not True:
                    if n_onset[k] == 0:
                        c = "grey"
                        alpha = 0.5
                    else:
                        c = "orangered"
                        alpha = n_onset[k] * alpha_g
                    if is_blocked[k] is None:
                        axes.scatter(axon_y[k], axon_z[k], marker="x", s=20, c="k")

                else:
                    if n_onset[k] == 0:
                        c = "seagreen"
                        alpha = 1
                    else:
                        c = "steelblue"
                        alpha = n_onset[k] * alpha_g

                axes.add_patch(
                    plt.Circle(
                        (axon_y[k], axon_z[k]),
                        axon_diam[k] / 2,
                        color=c,
                        fill=True,
                        alpha=alpha,
                    )
                )

            if self.extra_stim is not None:
                self.extra_stim.plot(axes=axes, color="gold", nerve_d=self.D)
            if num:
                for k in range(self.n_ax):
                    axes.text(
                        self.axons_y[k], self.axons_z[k], str(k)
                    )  # horizontalalignment='center',verticalalignment='center')
            axes.set_xlim(
                (
                    -1.1 * self.D / 2 + self.y_grav_center,
                    1.1 * self.D / 2 + self.y_grav_center,
                )
            )
            axes.set_ylim(
                (
                    -1.1 * self.D / 2 + self.z_grav_center,
                    1.1 * self.D / 2 + self.z_grav_center,
                )
            )
