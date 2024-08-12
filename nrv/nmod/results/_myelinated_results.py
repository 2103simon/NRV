"""
NRV-:class:`.myelinated_results` handling.
"""

import numpy as np
import matplotlib.pyplot as plt
from ._axons_results import axon_results
from ...backend._log_interface import rise_warning
from ...fmod.materials import is_mat, load_material
from ...utils.units import to_nrv_unit, convert


class myelinated_results(axon_results):
    """ """

    def __init__(self, context=None):
        super().__init__(context)

    def get_index_myelinated_sequence(self, n):
        """
        Returns the simulated myelination sequence of the axon corresponding to a calculation
        point index.

        Parameters
        ----------
        n     : int
            intex to check.

        Returns
        -------
        str
            corresponding sequence.
        """
        if self["rec"] == "nodes":
            return "node"
        else:
            if n > len(self["x_rec"]):
                rise_warning("index not in axon")
            # +1 required because nbr of computation point = nbr seg/sec + 1
            # see if it's a bug
            Nseg_per_sec = self["Nseg_per_sec"] + 1
            N_sec_type = 11
            seq_types = self["axon_path_type"]
            if n == 0:
                return seq_types[0]
            else:
                return seq_types[((n - 1) // Nseg_per_sec) % N_sec_type]

    def find_central_node_coordinate(self):
        """
        Returns the index of the closer node from the center

        Returns
        -------
        float
            x-position of the closer node from the center
        """
        return self["x_rec"][self.find_central_node_index()]

    def find_central_node_index(self):
        """
        Returns the index of the closer node from the center

        Returns
        -------
        int
            index of `x_rec` of the closer node from the center
        """
        n_center = len(self["x_rec"]) // 2
        if self["rec"] == "nodes":
            return n_center
        else:
            for i in range(n_center):
                if self.get_index_myelinated_sequence(n_center + i) == "node":
                    return n_center + i
                elif self.get_index_myelinated_sequence(n_center - i) == "node":
                    return n_center - i
        rise_warning("No node found in the axon")
        return n_center

    def get_myelin_properties(self, endo_mat=None):
        """
        compute the cutoff frequency of the axon's membrane and add it to the simulation results dictionnary
        NB: The frequency is computed in [kHz]

        Returns
        -------
        g_mye              : np.ndarray
            value of the cutoff conductivity of the axon's membrane
        c_mye              : np.ndarray
            value of the cutoff capacitance of the axon's membrane
        f_mye              : np.ndarray
            value of the cutoff frequency of the axon's membrane
        """
        if self["rec"] == "nodes":
            rise_warning("No myelin in the axon simulated, None returned")
            return None

        ax = self.generate_axon()
        self["g_mye"] = ax.get_myelin_conductance()
        if endo_mat is not None:
            if not is_mat(endo_mat):
                endo_mat = load_material(endo_mat)
            I = np.isclose(self["g_mye"], 1e10)
            self["g_mye"][I] *= 0.0
            self["g_mye"][I] += convert(endo_mat.sigma, "S/m**2", "S/cm**2")
        self["c_mye"] = ax.get_myelin_capacitance()
        self["f_mye"] = self["g_mye"] / (2 * np.pi * self["c_mye"])

        # in [MHz] as g_mem in [S/cm^{2}] and c_mem [uF/cm^{2}]
        # * [MHz] to convert to [kHz]
        self["f_mye"] = to_nrv_unit(self["f_mye"], "MHz")
        return self["g_mye"], self["c_mye"], self["f_mye"]

    def plot_x_t(
        self, axes: plt.axes, key: str = "V_mem", color: str = "k", **kwgs
    ) -> None:
        node_x = self.x[self.node_index]
        dx = np.abs(node_x[1] - node_x[0])
        rec_idx = self.node_index
        if not "ALL" in self.rec.upper():
            rec_idx = np.arange(len(node_x))
        norm_fac = dx / (np.max(abs(self[key])) * 1.1)
        offset = np.abs(np.min(self[key][0] * norm_fac))
        for node, node_idx in zip(node_x, rec_idx):
            axes.plot(
                self["t"],
                self[key][node_idx] * norm_fac + node + offset,
                color=color,
                **kwgs
            )

    def plot_Nav_states(ax: plt.axes) -> None:
        """
        Plot the state machine for kinetic (Markov) Nav 1.1 to 1.9 values

        Parameters
        ----------
        ax : matplotlib axis object
            axes of the figure to work on
        """

        values = []
        rise_warning("plot_Nav_states is not fully implemented")
        states = [r"$I_1$", r"$I_2$", r"$C_1$", r"$C_2$", r"$O_1$", r"$O_2$"]

        X = [-1, -3, 0, 1, 0, 3]
        Y = [0, 0, 1, 0, -1, 0]
        c = ["r", "r", "b", "b", "g", "g"]

        ax.set_xlim(-3.4, 3.4)
        ax.set_ylim(-1.5, 1.5)
        for i in range(len(states)):
            ax.scatter(X[i], Y[i], s=300 + values[i] * 1450, c=c[i], alpha=0.4)
            ax.text(X[i], Y[i], states[i], ha="center", va="center")
        # paths
        ax.arrow(
            -2.5, 0.03, 1, 0, linewidth=1, alpha=0.5, head_width=0.02, head_length=0.02
        )
        ax.text(-2, 0.2, "$I_2I_1$", ha="center", va="center", alpha=0.4)
        ax.arrow(
            -1.5,
            -0.03,
            -1,
            0,
            linewidth=1,
            alpha=0.5,
            head_width=0.02,
            head_length=0.02,
        )
        ax.text(-2, -0.2, "$I_1I_2$", ha="center", va="center", alpha=0.4)

        ax.arrow(
            -0.83,
            0.25,
            0.5,
            0.5,
            linewidth=1,
            alpha=0.5,
            head_width=0.02,
            head_length=0.02,
        )
        ax.text(-0.9, 0.6, "$I_1C_1$", ha="center", va="center", alpha=0.4)
        ax.arrow(
            -0.22,
            0.75,
            -0.5,
            -0.5,
            linewidth=1,
            alpha=0.5,
            head_width=0.02,
            head_length=0.02,
        )
        ax.text(-0.45, 0.25, r"$C_1I_1$", ha="center", va="center", alpha=0.4)

        ax.arrow(
            0.72,
            0.25,
            -0.5,
            0.5,
            linewidth=1,
            alpha=0.5,
            head_width=0.02,
            head_length=0.02,
        )
        ax.text(0.9, 0.6, r"$C_1C_2$", ha="center", va="center", alpha=0.4)
        ax.arrow(
            0.33,
            0.75,
            0.5,
            -0.5,
            linewidth=1,
            alpha=0.5,
            head_width=0.02,
            head_length=0.02,
        )
        ax.text(0.45, 0.25, r"$C_2C_1$", ha="center", va="center", alpha=0.4)

        ax.arrow(
            0.83,
            -0.25,
            -0.5,
            -0.5,
            linewidth=1,
            alpha=0.5,
            head_width=0.02,
            head_length=0.02,
        )
        ax.text(0.9, -0.6, r"$C_2O_1$", ha="center", va="center", alpha=0.4)
        ax.arrow(
            0.22,
            -0.75,
            0.5,
            0.5,
            linewidth=1,
            alpha=0.5,
            head_width=0.02,
            head_length=0.02,
        )
        ax.text(0.45, -0.25, r"$O_1C_2$", ha="center", va="center", alpha=0.4)

        ax.arrow(
            -0.33,
            -0.75,
            -0.5,
            0.5,
            linewidth=1,
            alpha=0.5,
            head_width=0.02,
            head_length=0.02,
        )
        ax.text(-0.9, -0.6, r"$O_1I_1$", ha="center", va="center", alpha=0.4)

        ax.arrow(
            1.5, 0.03, 1, 0, linewidth=1, alpha=0.5, head_width=0.02, head_length=0.02
        )
        ax.text(2, 0.2, r"$C_20_2$", ha="center", va="center", alpha=0.4)
        ax.arrow(
            2.5, -0.03, -1, 0, linewidth=1, alpha=0.5, head_width=0.02, head_length=0.02
        )
        ax.text(2, -0.2, r"$O_2C_2$", ha="center", va="center", alpha=0.4)
        # make axes to disappear
        ax.set_xticks([])
        ax.set_yticks([])
        ax.axis("off")
