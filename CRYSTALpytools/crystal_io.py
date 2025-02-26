#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Objects of input / output files of CRYSTAL. Methods to edit or substract data
from corresponding files are provided.
"""
from CRYSTALpytools import units
from CRYSTALpytools.base.crysd12 import Crystal_inputBASE


class Crystal_input(Crystal_inputBASE):
    """
    Crystal input object inherited from the :ref:`Crystal_inputBASE <ref-base-crysd12>`
    object. For the basic set-ups of keywords, please refer to manuals there.
    """
    def __init__(self):
        super(Crystal_input, self).__init__()

    def geom_from_cif(self, file, zconv=None, keyword='EXTERNAL',
                      pbc=[True, True, True], gui_name='fort.34',
                      symprec=0.01, angle_tolerance=5.0):
        """
        Read geometry from cif file and put infomation to geom block, either as
        'EXTERNAL' or 'CRYSTAL'. CIF files with a single geometry only.

        CIF with Symmetry is required.

        .. note::

            CIF files should have the '.cif' extension.

        Args:
            file (str): CIF file.
            keyword (str): 'EXTERNAL' or 'CRYSTAL'.
            zconv (list[list[int, int]]): 1st element: The **index** of atom;
                2nd element: The new conventional atomic number. Atoms of the
                irreducible unit is required.
            pbc (list[bool]): *Limited to keyword = EXTERNAL*. Periodic boundary
                conditions along x, y, z axis
            gui_name (str): *Limited to keyword = EXTERNAL*. Gui file's name.
            symprec (float): *Limited to keyword = CRYSTAL*. If not none,
                finds the symmetry of the structure. See `pymatgen.symmetry.analyzer.SpacegroupAnalyzer <https://pymatgen.org/pymatgen.symmetry.analyzer.html#pymatgen.symmetry.analyzer.SpacegroupAnalyzer>`_
            angle_tolerance (float): *Limited to keyword = CRYSTAL*. See `pymatgen.symmetry.analyzer.SpacegroupAnalyzer <https://pymatgen.org/pymatgen.symmetry.analyzer.html#pymatgen.symmetry.analyzer.SpacegroupAnalyzer>`_
        """
        import re
        from pymatgen.core.structure import IStructure

        struc = IStructure.from_file(file)
        self.geom_from_pmg(struc, zconv, keyword, pbc, gui_name, symprec, angle_tolerance)

        return self

    def geom_from_pmg(self, struc, zconv=None, keyword='EXTERNAL',
                      pbc=[True, True, True], gui_name='fort.34',
                      symprec=0.01, angle_tolerance=5.0):
        """
        Read geometry defined by PyMatGen structure object and put infomation
        into geom block, either as 'EXTERNAL' or 'CRYSTAL'.

        See ``geom_from_cif`` for definition of arguments.
        """
        import re
        from CRYSTALpytools.convert import cry_pmg2gui

        if re.match(r'^EXTERNAL$', keyword, re.IGNORECASE):
            super(Crystal_input, self).geom.external()
            gui = cry_pmg2gui(struc, pbc=pbc, symmetry=True, zconv=zconv)
            gui.write_gui(gui_name, symm=True)
        elif re.match(r'^CRYSTAL$', keyword, re.IGNORECASE):
            self._pmg2input(struc, zconv, symprec=symprec, angle_tolerance=angle_tolerance)
        else:
            raise ValueError("Input keyword format error: {}".format(keyword))

        return self

    def _pmg2input(self, struc, zconv=None, symprec=0.01, angle_tolerance=5.0):
        """
        Pymatgen IStructure object to 'CRYSTAL' input block

        .. note::

            Coordinates of corresponding atoms may not consistent with the
            original CIF file, in which case coordinates of another symmetry
            equivalent atom is used.

            When multiple choices of periodic cell exist, this method might
            lead to errors due to the inconsistent choice of periodic cell
            between CRYSTAL and pymatgen.
        """
        import numpy as np
        from pymatgen.core.structure import IStructure
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

        analyzer = SpacegroupAnalyzer(struc, symprec=symprec, angle_tolerance=angle_tolerance)
        # Analyze the refined geometry
        struc2 = analyzer.get_refined_structure()
        analyzer2 = SpacegroupAnalyzer(struc2, symprec=symprec, angle_tolerance=angle_tolerance)
        struc_pri = analyzer2.get_primitive_standard_structure()
        analyzer3 = SpacegroupAnalyzer(struc_pri, symprec=symprec, angle_tolerance=angle_tolerance)
        struc_pri = analyzer3.get_symmetrized_structure()

        sg = analyzer2.get_space_group_number()
        latt = []
        if sg >= 1 and sg < 3:  # trilinic
            for i in ['a', 'b', 'c', 'alpha', 'beta', 'gamma']:
                latt.append(round(
                    getattr(struc_pri.lattice, i), 6
                ))
        elif sg >= 3 and sg < 16:  # monoclinic
            for i in ['a', 'b', 'c', 'beta']:
                latt.append(round(
                    getattr(struc_pri.lattice, i), 6
                ))
        elif sg >= 16 and sg < 75:  # orthorhombic
            for i in ['a', 'b', 'c']:
                latt.append(round(
                    getattr(struc_pri.lattice, i), 6
                ))
        elif sg >= 75 and sg < 143:  # tetragonal
            for i in ['a', 'c']:
                latt.append(round(
                    getattr(struc_pri.lattice, i), 6
                ))
        elif sg >= 143 and sg < 168:  # trigonal, convert to hexagonal
            struc_pri = analyzer3.get_conventional_standard_structure()
            analyzer4 = SpacegroupAnalyzer(struc_pri, symprec=symprec, angle_tolerance=angle_tolerance)
            struc_pri = analyzer4.get_symmetrized_structure()
            for i in ['a', 'c']:
                latt.append(round(
                    getattr(struc_pri.lattice, i), 6
                ))
        elif sg >= 168 and sg < 195:  # hexagonal and trigonal
            for i in ['a', 'c']:
                latt.append(round(
                    getattr(struc_pri.lattice, i), 6
                ))
        else:  # cubic
            latt.append(round(struc_pri.lattice.a, 6))

        natom = len(struc_pri.equivalent_sites)
        eq_atom = int(len(struc_pri.species) / natom)
        atominfo = []
        if zconv != None:
            z_atom_index = [i[0] for i in zconv]
        for i in range(natom):
            idx_eq = int(i * eq_atom)
            if zconv == None:
                z_input = struc_pri.species[idx_eq].Z
            else:
                try:
                    atom_to_sub = z_atom_index.index(i)
                    z_input = zconv[atom_to_sub][1]
                except ValueError:
                    z_input = struc_pri.species[idx_eq].Z
            atominfo.append([
                '{:<3}'.format(z_input),
                '{0:11.8f}'.format(
                    round(struc_pri.equivalent_sites[i][0].frac_coords[0], 8)
                ),
                '{0:11.8f}'.format(
                    round(struc_pri.equivalent_sites[i][0].frac_coords[1], 8)
                ),
                '{0:11.8f}'.format(
                    round(struc_pri.equivalent_sites[i][0].frac_coords[2], 8)
                )
            ])

        super(Crystal_input, self).geom.crystal(IGR=sg, latt=latt, atom=atominfo)

        return


class Crystal_output:
    """This class reads a CRYSTAL output and generates an object."""

    def __init__(self):
        """Initialize the Crystal_output."""

        pass

    def read_cry_output(self, output_name):
        """Reads a CRYSTAL output file.
        
        Args:
            output_name (str): Name of the output file.
        Returns:
            CrystalOutput: Object representing the CRYSTAL output.
        """
        import sys
        import re

        self.name = output_name

        # Check if the file exists
        try:
            if output_name[-3:] != 'out' and output_name[-4:] != 'outp':
                output_name = output_name+'.out'
            file = open(output_name, 'r', errors='ignore')
            self.data = file.readlines()
            file.close()
        except:
            print('EXITING: a .out file needs to be specified')
            sys.exit(1)

        # Check the calculation terminated correctly
        self.terminated = False

        for i, line in enumerate(self.data[::-1]):
            if re.match(r'^ EEEEEEEEEE TERMINATION', line):
                self.terminated = True
                # This is the end of output
                self.eoo = len(self.data)-1-i
                break

        if self.terminated == False:
            self.eoo = len(self.data)

        # Check if the scf converged
        self.converged = False
        for line in self.data:
            if re.match(r'^ == SCF ENDED - CONVERGENCE ON ENERGY', line):
                self.converged = True
                break

        # Check if the geometry optimisation converged
        self.opt_converged = False

        for line in self.data[::-1]:
            if bool(re.search('OPT END - CONVERGED', line) ) == True:
                self.opt_converged = True
                break
        
        return self

    def get_dielectric_tensor(self):
        """Extracts the dielectric tensor from the output.
        
        Returns:
            list: Dielectric tensor values.
        """
        import re

        for i, line in enumerate(self.data):
            if re.match(r'^ TENSOR IN PRINCIPAL AXES SYSTEM', line):
                # This is the end of output
                self.dielectric_tensor = [
                    float(x) for x in self.data[i+1].split()[1::2]]
                return self.dielectric_tensor
        return None

    def get_eigenvectors(self):
        """Extracts eigenvectors from the output."""
        import re

        for i, line in enumerate(self.data):
            if re.match(r'\s NUMBER OF AO', line) != None:
                self.num_ao = int(line.split()[3])

            if re.match(r'\s SHRINK. FACT.(MONKH.)', line) != None:
                self.num_k = int(line.split()[13])

            if re.match(r'\s SHRINK. FACT.(MONKH.)', line) != None:
                self.num_k = int(line.split()[13])

    def get_dimensionality(self):
        """Gets the dimensionality of the system.
        
        Returns:
            int: Dimensionality of the system.
        """

        import re

        for line in self.data:
            if re.match(r'\sGEOMETRY FOR WAVE FUNCTION - DIMENSIONALITY OF THE SYSTEM', line) != None:
                self.dimensionality = int(line.split()[9])
                return self.dimensionality

    def get_final_energy(self):
        """Get the final energy of the system.
        
        Returns:
            float: The final energy of the system.
        """
        import re

        self.final_energy = None
        for line in self.data[self.eoo::-1]:
            if re.match(r'\s\W OPT END - CONVERGED', line) != None:
                self.final_energy = units.H_to_eV(float(line.split()[7]))
                return self.final_energy
            elif re.match(r'^ == SCF ENDED', line) != None:
                self.final_energy = units.H_to_eV(float(line.split()[8]))
                return self.final_energy

        if self.final_energy == None:
            print('WARNING: no final energy found in the output file. energy = None')

        return self.final_energy

    def get_scf_convergence(self, all_cycles=False):
        """Returns the scf convergence energy and energy difference.

        Args:
            all_cycles (bool, optional): Return all steps for a geometry opt. Defaults to False.
        Returns:
            tuple or list: The scf convergence energy and energy difference.
        """
        import re
        import numpy as np

        self.scf_energy = []
        self.scf_deltae = []

        scf_energy = []
        scf_deltae = []

        for line in self.data:

            if re.match(r'^ CYC ', line):
                scf_energy.append(float(line.split()[3]))
                scf_deltae.append(float(line.split()[5]))

            if re.match(r'^ == SCF ENDED - CONVERGENCE ON ENERGY', line):
                if all_cycles == False:
                    self.scf_energy = units.H_to_eV(np.array(scf_energy))
                    self.scf_deltae = units.H_to_eV(np.array(scf_deltae))

                    return self.scf_energy, self.scf_deltae

                elif all_cycles == True:
                    self.scf_energy.append(scf_energy)
                    self.scf_deltae.append(scf_deltae)
                    scf_energy = []
                    scf_deltae = []

            self.scf_convergence = [self.scf_energy, self.scf_deltae]
        return self.scf_convergence

    def get_opt_convergence_energy(self):
        """Returns the energy for each opt step.
        
        Returns:
            list: Energy for each optimization step.
        """
        self.opt_energy = []
        for line in self.data:
            if re.match(r'^ == SCF ENDED - CONVERGENCE ON ENERGY', line):
                self.opt_energy.append(units.H_to_eV(float(line.split()[8])))

        return self.opt_energy

    def get_num_cycles(self):
        """Returns the number of SCF cycles.
        
        Returns:
            int: Number of SCF cycles.
        """
        import re

        for line in self.data[::-1]:
            if re.match(r'^ CYC ', line):
                self.num_cycles = int(line.split()[1])
                return self.num_cycles
        return None

    def get_fermi_energy(self):
        """Returns the system Fermi energy.
        
        Returns:
            float: Fermi energy of the system.
        """
        import re

        self.fermi_energy = None

        for i, line in enumerate(self.data[len(self.data)::-1]):
            # This is in case the .out is from a BAND calculation
            if re.match(r'^ TTTTTTTTTTTTTTTTTTTTTTTTTTTTTT BAND', self.data[len(self.data)-(i+4)]) != None:
                for j, line1 in enumerate(self.data[len(self.data)-i::-1]):
                    if re.match(r'^ ENERGY RANGE ', line1):
                        self.fermi_energy = units.H_to_eV(
                            float(line1.split()[7]))
                        # Define from what type of calcualtion the Fermi energy was exctracted
                        self.efermi_from = 'band'
                        break
            # This is in case the .out is from a DOSS calculation
            if re.match(r'^ TTTTTTTTTTTTTTTTTTTTTTTTTTTTTT DOSS', self.data[len(self.data)-(i+4)]) != None:
                for j, line1 in enumerate(self.data[len(self.data)-i::-1]):
                    if re.match(r'^ N. OF SCF CYCLES ', line1):
                        self.fermi_energy = units.H_to_eV(
                            float(line1.split()[7]))
                        # Define from what type of calcualtion the Fermi energy was exctracted
                        self.efermi_from = 'doss'
                        break
            # This is in case the .out is from a sp/optgeom calculation
            # For non metals think about top valence band
            else:
                for j, line1 in enumerate(self.data[:i:-1]):
                    if re.match(r'^   FERMI ENERGY:', line1) != None:
                        self.fermi_energy = units.H_to_eV(
                            float(line1.split()[2]))
                        self.efermi_from = 'scf'
                        break
                    if re.match(r'^ POSSIBLY CONDUCTING STATE - EFERMI', line1) != None:
                        self.fermi_energy = units.H_to_eV(
                            float(line1.split()[5]))
                        self.efermi_from = 'scf'
                        break
                if self.fermi_energy == None:
                    for j, line1 in enumerate(self.data[:i:-1]):
                        if re.match(r'^ TOP OF VALENCE BANDS', line1) != None:
                            self.fermi_energy = units.H_to_eV(
                                float(line1.split()[10]))
                            self.efermi_from = 'scf_top_valence'
                            break

        if self.fermi_energy == None:
            print('WARNING: no Fermi energy found in the output file. efermi = None')

        return self.fermi_energy

    def get_primitive_lattice(self, initial=True):
        """Returns the primitive lattice of the system.

        Args:
            initial (bool): Determines whether to read the initial or last lattice vectors.
                Useful in case of optgeom. Defaults to True.
        Returns:
            np.ndarray: Primitive lattice of the system.
        """
        import re
        import numpy as np

        lattice = []
        self.primitive_lattice = None
        if initial == True:
            for i, line in enumerate(self.data):
                if re.match(r'^ DIRECT LATTICE VECTORS CARTESIAN', line):
                    for j in range(i+2, i+5):
                        lattice_line = [float(n) for n in self.data[j].split()]
                        lattice.append(lattice_line)
                    self.primitive_lattice = np.array(lattice)
                    break
        elif initial == False:
            for i, line in enumerate(self.data[::-1]):
                if re.match(r'^ DIRECT LATTICE VECTORS CARTESIAN', line):
                    for j in range(len(self.data)-i+1, len(self.data)-i+4):
                        lattice_line = [float(n) for n in self.data[j].split()]
                        lattice.append(lattice_line)
                    self.primitive_lattice = np.array(lattice)
                    break

        if lattice == []:
            print('WARNING: no lattice vectors found in the output file. lattice = []')

        return self.primitive_lattice

    def get_reciprocal_lattice(self, initial=True):
        """Returns the reciprocal primitive lattice of the system.

        Args:
            initial (bool): Determines whether to read the initial or last reciprocal lattice vectors.
                Useful in case of optgeom. Defaults to True.
        Returns:
            np.ndarray: Reciprocal primitive lattice of the system.
        """
        import re
        import numpy as np

        lattice = []
        if initial == True:
            for i, line in enumerate(self.data):
                if re.match(r'^ DIRECT LATTICE VECTORS COMPON. \(A.U.\)', line):
                    for j in range(i+2, i+5):
                        lattice_line = [
                            units.angstrom_to_au(float(n)) for n in self.data[j].split()[3:]]
                        lattice.append(lattice_line)
                    self.reciprocal_lattice = np.array(lattice)
                    return self.reciprocal_lattice
        elif initial == False:
            for i, line in enumerate(self.data[::-1]):
                if re.match(r'^ DIRECT LATTICE VECTORS COMPON. \(A.U.\)', line):
                    for j in range(len(self.data)-i+1, len(self.data)-i+4):
                        lattice_line = [
                            angstrom_to_au(float(n)) for n in self.data[j].split()[3:]]
                        lattice.append(lattice_line)
                    self.reciprocal_lattice = np.array(lattice)
                    return self.reciprocal_lattice

        return None

    def get_band_gap(self):
        """Returns the system band gap.
        
        Returns:
            float or np.ndarray: Band gap of the system.
        """
        import re
        import numpy as np

        # Check if the system is spin polarised
        self.spin_pol = False
        for line in self.data:
            if re.match(r'^ SPIN POLARIZED', line):
                self.spin_pol = True
                break

        for i, line in enumerate(self.data[len(self.data)::-1]):
            if self.spin_pol == False:
                if re.match(r'^\s\w+\s\w+ BAND GAP', line):
                    self.band_gap = float(line.split()[4])
                    return self.band_gap
                elif re.match(r'^\s\w+ ENERGY BAND GAP', line):
                    self.band_gap = float(line.split()[4])
                    return self.band_gap
                elif re.match(r'^ POSSIBLY CONDUCTING STATE', line):
                    self.band_gap = False
                    return self.band_gap
            else:
                # This might need some more work
                band_gap_spin = []
                if re.match(r'\s+ BETA \s+ ELECTRONS', line):
                    band_gap_spin.append(
                        float(self.data[len(self.data)-i-3].split()[4]))
                    band_gap_spin.append(
                        float(self.data[len(self.data)-i+3].split()[4]))
                    self.band_gap = np.array(band_gap_spin)
                    return self.band_gap
        if self.spin_pol == True and band_gap_spin == []:
            print(
                'DEV WARNING: check this output and the band gap function in crystal_io')

    def get_last_geom(self, write_gui_file=True, symm_info='pymatgen'):
        """
        Return the last optimised geometry

        Args:
            write_gui_file (bool): Whether to write the last geometry to gui
                file.
            symm_info (str): 'pymatgen' to use symmetry info from a pymatgen
                object, otherwise it is taken from the existing gui file
        """
        import re
        from mendeleev import element
        import numpy as np
        from pymatgen.core.structure import Structure, Molecule
        from CRYSTALpytools.convert import cry_pmg2gui

        dimensionality = self.get_dimensionality()

        # Find the last geometry
        for i, line in enumerate(self.data):
            if re.match(r' TRANSFORMATION MATRIX PRIMITIVE-CRYSTALLOGRAPHIC CELL', line):
                trans_matrix_flat = [float(x) for x in self.data[i+1].split()]
                self.trans_matrix = []
                for i in range(0, len(trans_matrix_flat), 3):
                    self.trans_matrix.append(trans_matrix_flat[i:i+3])
                self.trans_matrix = np.array(self.trans_matrix)

        for i, line in enumerate(self.data[len(self.data)::-1]):
            if re.match(r'^ T = ATOM BELONGING TO THE ASYMMETRIC UNIT', line):
                self.n_atoms = int(self.data[len(self.data)-i-3].split()[0])
                self.atom_positions = []
                self.atom_symbols = []
                self.atom_numbers = []

                for j in range(self.n_atoms):
                    atom_line = self.data[len(
                        self.data)-i-2-int(self.n_atoms)+j].split()[3:]
                    self.atom_symbols.append(str(atom_line[0]))

                    self.atom_positions.append(
                        [float(x) for x in atom_line[1:]])  # These are fractional

                for atom in self.atom_symbols:
                    self.atom_numbers.append(
                        element(atom.capitalize()).atomic_number)

                self.atom_positions_cart = np.array(self.atom_positions)

                if dimensionality > 0:
                    lattice = self.get_primitive_lattice(initial=False)
                else:
                    min_max = max([
                        (max(self.atom_positions_cart[:, 0]) -
                         min(self.atom_positions_cart[:, 0])),
                        (max(self.atom_positions_cart[:, 1]) -
                         min(self.atom_positions_cart[:, 1])),
                        (max(self.atom_positions_cart[:, 2]) -
                         min(self.atom_positions_cart[:, 2]))
                    ])
                    lattice = np.identity(3)*(min_max+10)

                if dimensionality > 0:
                    self.atom_positions_cart[:, :dimensionality] = np.matmul(
                        np.array(self.atom_positions)[:, :dimensionality], lattice[:dimensionality, :dimensionality])

                self.cart_coords = []

                for i in range(len(self.atom_numbers)):
                    self.cart_coords.append([self.atom_numbers[i], self.atom_positions_cart[i]
                                             [0], self.atom_positions_cart[i][1], self.atom_positions_cart[i][2]])
                self.cart_coords = np.array(self.cart_coords)

                if dimensionality > 0:
                    lattice = self.get_primitive_lattice(initial=False)
                else:
                    min_max = max([
                        (max(self.cart_coords[:, 0]) -
                         min(self.cart_coords[:, 0])),
                        (max(self.cart_coords[:, 1]) -
                         min(self.cart_coords[:, 1])),
                        (max(self.cart_coords[:, 2]) -
                         min(self.cart_coords[:, 2]))
                    ])
                    lattice = np.identity(3)*(min_max+10)

                # Write the gui file
                if write_gui_file == True:
                    # Write the gui file
                    # This is a duplication from write_gui, but the input is different
                    # It requires both the output and gui files with the same name and in the same directory
                    if symm_info == 'pymatgen':
                        if self.name[-3:] == 'out':
                            gui_file = self.name[:-4]+'.gui'

                        elif self.name[-4:] == 'outp':
                            gui_file = self.name[:-5]+'.gui'
                        else:
                            gui_file = self.name+'.gui'

                        structure = Structure(lattice, self.atom_numbers,
                                              self.atom_positions_cart, coords_are_cartesian=True)
                        if dimensionality == 0:
                            pbc = [False, False, False]
                        elif dimensionality == 1:
                            pbc = [True, False, False]
                        elif dimensionality == 2:
                            pbc = [True, True, False]
                        else:
                            pbc = [True, True, True]
                        gui_object = cry_pmg2gui(structure, pbc=pbc)

                        gui_object.write_gui(gui_file)
                    else:
                        gui_file = symm_info
                        try:
                            file = open(gui_file, 'r')
                            gui_data = file.readlines()
                            file.close()
                        except:
                            raise FileNotFoundError(
                                'A .gui file with the same name as the input need to be present in the directory.')
                        # Replace the lattice vectors with the optimised ones
                        for i, vector in enumerate(lattice.tolist()):
                            gui_data[i+1] = ' '.join([str(x)
                                                      for x in vector])+'\n'

                        n_symmops = int(gui_data[4])
                        for i in range(len(self.atom_numbers)):
                            gui_data[i+n_symmops*4+6] = '{} {}\n'.format(
                                self.atom_numbers[i], ' '.join(str(x) for x in self.atom_positions_cart[i][:]))

                        with open(gui_file[:-4]+'_last.gui', 'w') as file:
                            for line in gui_data:
                                file.writelines(line)

                self.last_geom = [lattice.tolist(
                ), self.atom_numbers, self.atom_positions_cart.tolist()]

                return self.last_geom

    def get_symm_ops(self):
        """Return the symmetry operators
        
        Returns:
            numpy.ndarray: Symmetry operators
        """
        import re
        import numpy as np

        symmops = []

        for i, line in enumerate(self.data):
            if re.match(r'^ \*\*\*\*   \d+ SYMMOPS - TRANSLATORS IN FRACTIONAL UNITS', line):
                self.n_symm_ops = int(line.split()[1])
                for j in range(0, self.n_symm_ops):
                    symmops.append([float(x)
                                    for x in self.data[i+3+j].split()[2:]])
                self.symm_ops = np.array(symmops)

                return self.symm_ops

    def get_forces(self, initial=False, grad=False):
        """
        Return the forces from an optgeom calculation
        
        Args:
            initial (bool, optional): Return forces from the initial calculation. Defaults to False.
            grad (bool, optional): Return gradient information. Defaults to False.
        Returns:
            list or None: Forces if available, None otherwise
        """
        if ' OPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPTOPT\n' not in self.data:
            print('WARNING: this is not a geometry optimisation.')
            return None
        else:

            import re
            import numpy as np

            self.forces_atoms = []
            self.forces_cell = []

            # Number of atoms
            for i, line in enumerate(self.data[len(self.data)::-1]):
                if re.match(r'^ T = ATOM BELONGING TO THE ASYMMETRIC UNIT', line):
                    self.n_atoms = int(
                        self.data[len(self.data)-i-3].split()[0])
                    break

            if grad == True:
                self.grad = []
                self.rms_grad = []
                self.disp = []
                self.rms_disp = []
                for i, line in enumerate(self.data):
                    if re.match(r'^ MAX GRADIENT', line):
                        self.grad.append(line.split()[2])
                    if re.match(r'^ RMS GRADIENT', line):
                        self.rms_grad.append(line.split()[2])
                    if re.match(r'^ MAX DISPLAC.', line):
                        self.disp.append(line.split()[2])
                    if re.match(r'^ RMS DISPLAC.', line):
                        self.rms_disp.append(line.split()[2])

            if initial == True:
                for i, line in enumerate(self.data):
                    if re.match(r'^ CARTESIAN FORCES IN HARTREE/BOHR \(ANALYTICAL\)', line):
                        for j in range(i+2, i+2+self.n_atoms):
                            self.forces_atoms.append(
                                [float(x) for x in self.data[j].split()[2:]])
                        self.forces_atoms = np.array(self.forces_atoms)
                    if re.match(r'^ GRADIENT WITH RESPECT TO THE CELL PARAMETER IN HARTREE/BOHR', line):
                        for j in range(i+4, i+7):
                            self.forces_cell.append(
                                [float(x) for x in self.data[j].split()])
                        self.forces_cell = np.array(self.forces_cell)
                        self.forces = [self.forces_cell, self.forces_atoms]
                        return self.forces

            elif initial == False:
                for i, line in enumerate(self.data[::-1]):
                    if re.match(r'^ GRADIENT WITH RESPECT TO THE CELL PARAMETER IN HARTREE/BOHR', line):
                        for j in range(len(self.data)-i+3, len(self.data)-i+6):
                            self.forces_cell.append(
                                [float(x) for x in self.data[j].split()])
                        self.forces_cell = np.array(self.forces_cell)

                    if re.match(r'^ CARTESIAN FORCES IN HARTREE/BOHR \(ANALYTICAL\)', line):
                        for j in range(len(self.data)-i+1, len(self.data)-i+1+self.n_atoms):
                            self.forces_atoms.append(
                                [float(x) for x in self.data[j].split()[2:]])
                        self.forces_atoms = np.array(self.forces_atoms)
                        self.forces = [self.forces_cell, self.forces_atoms]
                        return self.forces

    def get_mulliken_charges(self):
        """
        Return the Mulliken charges (PPAN keyword in input)
        
        Returns:
            list: Mulliken charges
        """
        import re

        self.mulliken_charges = []
        for i, line in enumerate(self.data):
            if re.match(r'^ MULLIKEN POPULATION ANALYSIS', line):
                for j in range(len(self.data[i:])):
                    line1 = self.data[i+4+j].split()
                    if line1 == []:
                        return self.mulliken_charges
                    elif line1[0].isdigit() == True:
                        self.mulliken_charges.append(float(line1[3]))
        return self.mulliken_charges

    def get_config_analysis(self,return_multiplicity=False):
        """
        Return the configuration analysis for solid solutions (CONFCON keyword in input)
        
        Args:
            return_multiplicity (bool, optional): Return multiplicity information. Defaults to False.
        Returns:
            list or str: Configuration analysis if available, or a warning message
        """
        import re
        import numpy as np

        # Check this is a configuration analysis calculation
        try:
            begin = self.data.index(
                '                             CONFIGURATION ANALYSIS\n')
        except:
            return "WARNING: this is not a CONFCNT analysis."

        for line in self.data[::-1]:
            if '----' in line:
                dash_line = line.rstrip().lstrip()
                break

        for i, line in enumerate(self.data[begin:]):
            if re.match(r'^ COMPOSITION', line):
                self.n_classes = line.split()[9]
                original_atom = str(line.split()[2])
                begin = begin+i
        config_list = []

        # Read all the configurations
        for line in self.data[begin:]:
            if not re.match(r'^   WARNING', line):
                config_list.extend(line.split())
        config_list = np.array(config_list)
        warning = np.where(config_list == 'WARNING')
        config_list = np.delete(config_list, warning)
        atom1_begin = np.where(config_list == original_atom)[0]
        atom1_end = np.where(
            config_list == dash_line)[0]
        atom2_begin = np.where(config_list == 'XX')[0]
        atom2_end = np.where(
            config_list == '<><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>')[0]
        end = np.where(
            config_list == '===============================================================================')[0][-1]
        atom2_end = np.append(atom2_end, end)
        atom_type1 = []
        atom_type2 = []
        multiplicity_tmp = config_list[np.where(config_list == 'MULTIPLICITY')[0]+2]
        multiplicity = [int(x) for x in multiplicity_tmp]
        config_list = config_list.tolist()
        for i in range(len(atom1_end)):
            atom_type1.append(
                [int(x) for x in config_list[atom1_begin[i+1]+1:atom1_end[i]]])
            atom_type2.append(
                [int(x) for x in config_list[atom2_begin[i]+1:atom2_end[i]]])

        self.atom_type1 = atom_type1
        self.atom_type2 = atom_type2

        self.multiplicity = multiplicity
        if return_multiplicity == True:
            return [self.atom_type1, self.atom_type2, multiplicity]
        else:
            return [self.atom_type1, self.atom_type2]

    def get_phonon(self, read_eigvt=False, rm_imaginary=True, rm_overlap=True,
                   imaginary_tol=-1e-4, q_overlap_tol=1e-4):
        """
        Read phonon-related properties from output file.

        Args:
            read_eigvt (bool): Whether to read phonon eigenvectors and
                normalize it to 1.
            rm_imaginary (bool): Remove the modes with negative frequencies and
                set all the related properties to NaN.
            rm_overlap (bool): *For dispersion calculations* Remove repeated q
                points and recalculate their weights.
            imaginary_tol (float): *``rm_imaginary`` = True only* The threshold
                of negative frequencies.
            q_overlap_tol (float): *``rm_overlap`` = True only* The threshold of
                overlapping points, defined as the 2nd norm of the difference
                of fractional q vectors

        .. note::

            In QHA calculations, the 'q point' dimension refer to harmonic
            phonons computed. In other cases it refers to points in reciprocal
            space.

        Returns:
            self.edft (array[float]): :math:`E_{0}` Energy with empirical
                correction. Unit: kJ/mol.
            self.nqpoint (int): Number of q points
            self.qpoint (list[list[array[float], float]]): A nqpoint\*1 list of
                2\*1 list whose first element is a 3\*1 array of fractional
                coordinates and the second is its weight.
            self.nmode (array[int]): Number of modes at q point. nqpoint\*1
                array.
            self.frequency (array[float]): nqpoint\*nmode array ofvibrational
                frequency. Unit: THz
            self.intens (array[float]): nqpoint\*nmode array of harmonic
                intensiy. Unit: km/mol
            self.IR (array[bool]): nqpoint\*nmode array of boolean values
                specifying whether the mode is IR active
            self.Raman (array[bool]): nqpoint\*nmode array of boolean values
                specifying whether the mode is Raman active
            self.eigenvector (array[float]): *``read_eigvt = True only``* 
                nqpoint\*nmode\*natom\*3 array of eigenvectors. Normalized to 1.
        """
        import re
        import numpy as np
        from CRYSTALpytools.base.crysout import PhononBASE
        from CRYSTALpytools.units import H_to_kjmol

        is_freq = False
        self.edft = []
        self.nqpoint = 0
        self.qpoint = []
        self.nmode = []
        self.frequency = []
        self.intens = []
        self.IR = []
        self.Raman = []
        self.eigenvector = []

        countline = 0
        while countline < len(self.data):
            line = self.data[countline]
            # Whether is a frequency file
            if re.match(r'^\s*\+\+\+\sSYMMETRY\sADAPTION\sOF\sVIBRATIONAL\sMODES\s\+\+\+', line):
                is_freq = True
                countline += 1
                continue
            # E_0 with empirical corrections
            elif re.match(r'^\s+CENTRAL POINT', line):
                self.edft.append(float(line.strip().split()[2]))
                countline += 1
                continue
            # Q point info + frequency
            ## Dispersion
            elif re.match(r'^.+EXPRESSED IN UNITS\s+OF DENOMINATOR', line):
                shrink = int(line.strip().split()[-1])
                countline += 1
                continue
            elif re.match(r'\s+DISPERSION K POINT NUMBER', line):
                coord = np.array(line.strip().split()[7:10], dtype=float)
                weight = float(line.strip().split()[-1])
                self.qpoint.append([coord / shrink, weight])
                self.nqpoint += 1
                countline += 2
                ## Read phonons
                phonon = PhononBASE.readmode_basic(self.data, countline)
                countline = phonon[0]
                self.frequency.append(phonon[1])
                self.intens.append(phonon[2])
                self.IR.append(phonon[3])
                self.Raman.append(phonon[4])
            ## Gamma point
            elif re.match(r'^\s+MODES\s+EIGV\s+FREQUENCIES\s+IRREP', line) and self.nqpoint == 0:
                countline += 2
                ## Read phonons
                phonon = PhononBASE.readmode_basic(self.data, countline)
                countline = phonon[0]
                self.frequency.append(phonon[1])
                self.intens.append(phonon[2])
                self.IR.append(phonon[3])
                self.Raman.append(phonon[4])
            ## Phonon eigenvector
            elif re.match(r'^\s+MODES IN PHASE', line) or re.match(r'^\s+NORMAL MODES NORMALIZED', line):
                if read_eigvt == False:
                    countline += 1
                    continue
                countline += 2
                eigvt = PhononBASE.readmode_eigenvector(self.data, countline)
                countline = eigvt[0]
                self.eigenvector.append(eigvt[1])
            # Other data
            else:
                countline += 1
                continue

        if is_freq == False:
            raise Exception('Not a frequency calculation.')

        # HA/QHA Gamma point calculation
        if self.nqpoint == 0:
            self.nqpoint = len(self.edft)
            self.qpoint = [[np.zeros([3,]), 1.] for i in range(self.nqpoint)]
            if len(self.edft) == 1:
                self.edft = [self.edft[0] for i in range(self.nqpoint)]
        # Dispersion
        else:
            self.qpoint = [[i[0], i[1] / self.nqpoint] for i in self.qpoint]
            self.edft = [self.edft[0] for i in range(self.nqpoint)]

        self.edft = H_to_kjmol(np.array(self.edft))

        self.frequency = np.array(self.frequency)
        self.nmode = np.array([len(i) for i in self.frequency], dtype=int)
        if self.intens[0] == []:
            self.intens = []
            self.IR = []
            self.Raman = []
        else:
            self.intens = np.array(self.intens)

        if self.eigenvector != []:
            self.eigenvector = np.array(self.eigenvector)


        if rm_imaginary == True:
            self = PhononBASE.clean_imaginary(self, threshold=imaginary_tol)

        if rm_overlap == True and self.nqpoint > 1:
            self = PhononBASE.clean_q_overlap(self, threshold=q_overlap_tol)

        return self

    def get_q_info(self):
        """
        Deprecated.
        """
        import warnings

        warnings.warn('This method is deprecated. Use `get_phonon`.', stacklevel=2)
        return self

    def get_mode(self):
        """
        Deprecated.
        """
        return self.get_q_info()

    def get_phonon_eigenvector(self):
        """
        Deprecated.
        """
        return self.get_q_info()

    def get_elatensor(self):
        """
        Extracts the elastic tensor from the data.

        Returns:
            list: Symmetrized elastic tensor as a 6x6 nested list.
        """
        startstring = " SYMMETRIZED ELASTIC"
        stopstring = " ELASTIC MODULI"
        self.tensor = []
        buffer = []
        strtensor = []
        copy = False

        # Search for elastic tensor and save it into buffer
        for line in self.data:
            if line.startswith(startstring):
                copy = True
            elif line.startswith(stopstring):
                copy = False
            elif copy:
                buffer.append(line)

        # Build tensor
        for i in range(6):
            # Clean buffer and copy it in strtensor
            strtensor.append(
                buffer[i + 1].replace(" |", " ").replace("\n", ""))
            # Split strtensor strings and copy them in tensor
            self.tensor.append(strtensor[i].split())
            # Conversion str -> float
            for j in range(6 - i):
                self.tensor[i][j] = float(self.tensor[i][j])
            # Add zeros
            for k in range(i):
                self.tensor[i].insert(0, 0)
        buffer.clear()

        # Symmetrize tensor
        for i in range(6):
            for j in range(6):
                self.tensor[j][i] = self.tensor[i][j]

        return self.tensor


class Properties_input:
    """Create a properties_input object"""


    def __init__(self, input_name=None):
        """Initialise the object"""

        self.is_newk = False

    def from_file(self, input_name):
        """
        Read the properties input from a file.
        
        Args:
            input_name (str): The name of the input file.
        Returns:
            self (Properties_input): The Properties_input object.
        """
        import sys

        self.name = input_name
        if input_name is not None:
            try:
                if input_name[-3:] != 'd12':
                    input_name = input_name+'.d12'
                file = open(input_name, 'r')
                self.data = file.readlines()
                file.close()
            except:
                print('EXITING: a .d3 file needs to be specified')
                sys.exit(1)

            # Check if NEWK is in the input
            if 'NEWK\n' in self.data:
                self.is_newk = True
                self.newk_block = self.data[0:2]
                self.property_block = self.data[2:]
            else:
                self.is_newk = False
                self.property_block = self.data

        return self

    def make_newk_block(self, shrink1, shrink2, Fermi=1, print_option=0):
        """
        Returns the newk block.
        
        Args:
            shrink1 (int): The first newk shrinking factor.
            shrink2 (int): The second newk shrinking factor.
            Fermi (int): Fermi recalculation option (default is 1).
            print_option (int): Properties printing option (default is 0).
        """

        self.is_newk = True

        self.newk_block = ['NEWK\n', '%s %s\n' % (shrink1, shrink2),
                           '%s %s\n' % (Fermi, print_option)]

    def make_bands_block(self, k_path, n_kpoints, first_band, last_band, print_eig=0, print_option=1,
                         title='BAND STRUCTURE CALCULATION'):
        """
        Returns the bands block for a bands calculation.
        
        Args:
            k_path (list or HighSymmKpath): The k-path for the bands calculation.
            n_kpoints (int): The number of k-points along the path.
            first_band (int): The index of the first band.
            last_band (int): The index of the last band.
            print_eig (int): Printing options for eigenvalues (default is 0).
            print_option (int): Properties printing options (default is 1).
            title (str): The title of the calculation (default is 'BAND STRUCTURE CALCULATION').
        """

        import numpy as np
        import sys

        bands_block = []

        # path from a pymatgen k_path object
        if 'HighSymmKpath' in str(type(k_path)):
            k_path_flat = [item for sublist in k_path.kpath['path']
                           for item in sublist]
            k_path_pmg = []
            for i in k_path_flat:
                # This is a pmg HighSymmKpath object
                k_path_pmg.append(k_path.kpath['kpoints'][i].tolist())
            k_path = np.array(k_path_pmg)

        elif type(k_path[0]) == list:
            # This is a list of lists
            k_path = np.array(k_path)

        else:
            print('EXITING: k_path type must be a list of list (k coordinates) or\
                a pymatgen HighSymmKpath object. %s selected' % type(k_path))
            sys.exit(1)

        k_unique = np.unique(k_path)

        # Find the shrinking factor
        k_unique = np.array(np.around(k_unique, 4)*10000, dtype=int)
        if len(k_unique) > 2:
            gcd = np.gcd.reduce(k_unique)
        else:
            gcd = np.gcd(k_unique[0], k_unique[1])
        k_path = np.array((k_path/gcd)*10000, dtype=int)
        shrink = int(10000/gcd)

        bands_block.append('BAND\n')
        bands_block.append(title+'\n')

        bands_block.append(str(len(k_path)-1)+' '+str(shrink)+' '+str(n_kpoints) +
                           ' '+str(first_band)+' '+str(last_band)+' ' +
                           str(print_option)+' '+str(print_eig)+'\n')

        # Add the symmetry lines
        for i in range(len(k_path[:-1])):
            bands_block.append(' '.join([str(x) for x in k_path[i]])+'  ' +
                               ' '.join([str(x) for x in k_path[i+1]])+'\n')

        bands_block.append('END\n')

        self.property_block = bands_block

        return self

    def make_doss_block(self, n_points=200, band_range=None, e_range=None, plotting_option=2,
                        poly=12, print_option=1):
        """
        Returns the doss block for a doss calculation.
        
        Args:
            n_points (int): The number of points in the DOS plot (default is 200).
            band_range (list or tuple): The range of bands to include in the DOS calculation (default is None).
            e_range (list or tuple): The energy range for the DOS calculation (default is None).
            plotting_option (int): DOS plotting options (default is 2).
            poly (int): Degree of the polynomial for smearing (default is 12).
            print_option (int): Properties printing options (default is 1).
        """

        import sys

        # either band_range or e_range needs to be specified
        doss_block = []
        if band_range == None and e_range == None:
            print('EXITING: please specify either band_range or e_range. None selected')
            sys.exit(1)
        elif band_range != None and e_range != None:
            print('EXITING: please specify either band_range or e_range. Both selected')
            sys.exit(1)
        elif type(band_range) == list and len(band_range) == 2:
            doss_range = band_range
        elif type(e_range) == list and len(e_range) == 2:
            doss_range = [-1, -1]

        else:
            print('EXITING: either the band_range argument or the e_range argument\
                do not match the required format (2 item list)')
            sys.exit(1)

        doss_block.append('DOSS\n')
        doss_block.append(str(0)+' '+str(n_points)+' '+str(doss_range[0])+' ' +
                          str(doss_range[1])+' '+str(plotting_option)+' '+str(poly)+' ' +
                          str(print_option)+'\n')

        if doss_range == [-1, -1]:
            doss_block.append(
                str(units.eV_to_H(e_range[0]))+' '+str(units.eV_to_H(e_range[1]))+'\n')

        doss_block.append('END\n')

        self.property_block = doss_block

        return self

    def make_pdoss_block(self, projections, proj_type='atom', output_file=None, n_points=200, band_range=None,
                         e_range=None, plotting_option=2, poly=12, print_option=1):
        """
        Returns the pdoss block for a pdoss calculation.

        Args:
            projections (dict): Dictionary specifying the projections for the pdoss calculation.
            proj_type (str): Type of projection ('atom' or 'site') (default is 'atom').
            output_file (str): Output file name (default is None).
            n_points (int): The number of points in the DOS plot (default is 200).
            band_range (list or tuple): The range of bands to include in the DOS calculation (default is None).
            e_range (list or tuple): The energy range for the DOS calculation (default is None).
            plotting_option (int): DOS plotting options (default is 2).
            poly (int): Degree of the polynomial for smearing (default is 12).
            print_option (int): Properties printing options (default is 1).
        """

        import sys

        pdoss_block = []
        if band_range == None and e_range == None:
            print('EXITING: please specify either band_range or e_range. None selected')
            sys.exit(1)
        elif band_range != None and e_range != None:
            print('EXITING: please specify either band_range or e_range. Both selected')
            sys.exit(1)
        elif type(band_range) == list and len(band_range) == 2:
            pdoss_range = band_range
            range_is_bands = True
        elif type(e_range) == list and len(e_range) == 2:
            pdoss_range = [-1, -1]
            range_is_bands = False

        else:
            print('EXITING: either the band_range argument or the e_range argument\
                do not match the required format (2 item list)')
            sys.exit(1)

        pdoss_block.append('DOSS\n')
        pdoss_block.append(str(len(projections))+' '+str(n_points)+' '+str(pdoss_range[0])+' ' +
                           str(pdoss_range[1])+' '+str(plotting_option)+' '+str(poly)+' ' +
                           str(print_option)+'\n')

        if range_is_bands == False:
            pdoss_block.append(
                str(round(units.eV_to_H(e_range[0]), 6))+' '+str(round(units.eV_to_H(e_range[1]), 6))+'\n')

        flat_proj = [x for sublist in projections for x in sublist]

        if all(isinstance(x, int) for x in flat_proj):
            if proj_type == 'atom':
                for proj in projections:
                    pdoss_block.append(str(-len(proj))+' ' +
                                       ' '.join([str(x) for x in proj])+'\n')
            if proj_type == 'ao':
                for proj in projections:
                    pdoss_block.append(str(len(proj))+' ' +
                                       ' '.join([str(x) for x in proj])+'\n')
            elif proj_type != 'atom' and proj_type != 'ao':
                print(
                    'EXITING: please specify either atom or ao projection. %s selected' % proj_type)
                sys.exit(1)
        elif all(isinstance(x, str) for x in flat_proj):
            if output_file == None:
                print(
                    'EXITING: please specify an outut file to use the atoms projection.')
                sys.exit(1)
            else:
                output = Crystal_output(output_file)
                output.get_last_geom()
                atoms_symbols = output.atom_symbols
                atoms_symbols.insert(0, 0)

                for proj in projections:
                    atom_positions_list = []
                    for element in proj:
                        index = [i for i, ele in enumerate(
                            atoms_symbols) if ele == element.upper()]
                        atom_positions_list.append([str(x) for x in index])
                    pdoss_block.append(
                        str(-len(index))+' '+' '.join([str(x) for x in index])+'\n')

        pdoss_block.append('END\n')

        self.property_block = pdoss_block

        return self

    def write_properties_input(self, input_name):
        """
        Writes the properties input to a file.

        Args:
            input_name (str): The name of the output file.
        """

        import sys
        import itertools

        if self.is_newk == False:
            property_input_list = self.property_block
        if self.is_newk == True:
            property_input_list = list(itertools.chain(
                self.newk_block, self.property_block))

        with open(input_name, 'w') as file:
            for line in property_input_list:
                file.writelines(line)


class Properties_output:
    """Creates a Properties_output object."""

    def __init__(self):
        """Initialize the Properties_output object."""

        pass

    def read_file(self, properties_output):
        """Parse the properties output file.
        
        Args:
            properties_output (str): The properties output file.
        Returns:
            Properties_output: The updated Properties_output object.
        """
        import os

        self.file_name = properties_output

        try:
            file = open(self.file_name, 'r')
            self.data = file.readlines()
            file.close()

            # directory
            dir_name = os.path.split(properties_output)[0]
            self.abspath = os.path.join(dir_name)

            # title (named "title" only to distinguish from "file_name" which means another thing)
            self.title = os.path.split(properties_output)[1]

        except:
            raise FileNotFoundError('EXITING: a CRYSTAL properties file needs to be specified')

    def read_vecfield(self, properties_output, which_prop):
        """Read the .f25 file to return a data array containing one or more density properties.
        
        Args:
            properties_output (str): The properties output file.
            which_prop (str): The density property selected by the user.
        Returns:
            Properties_output: The updated Properties_output object.
        """

        import numpy as np

        self.read_file(properties_output)

        data = self.data

        # Reads the header information
        nrow = int(data[0].split()[1])
        ncol = int(data[0].split()[2])
        stepx = float(data[0].split()[3])
        stepy = float(data[0].split()[4])
        cosxy = float(data[0].split()[5])

        A = np.array([float(data[1].split()[0]), float(
            data[1].split()[1]), float(data[1].split()[2])])
        B = np.array([float(data[1].split()[3]), float(
            data[1].split()[4]), float(data[1].split()[5])])

        C = np.array([float(data[2].split()[0]), float(
            data[2].split()[1]), float(data[2].split()[2])])
        naf = int(data[2].split()[3])
        ldim = int(data[2].split()[4])

        self.header = (nrow, ncol, stepx, stepy, cosxy, A, B, C, naf, ldim)

        # Elaborates the header data
        skip = 6 + naf

        for i in range(2, 20):
            if (nrow % i) == 0:
                nrow_split = int(nrow/i)

        for i in range(2, 20):
            if (ncol % i) == 0:
                ncol_split = int(ncol/i)

        blines = (nrow*ncol)/6
        if (blines % 6) == 0:
            blines = int(blines)
        else:
            blines = int(blines) + 1

        # Reads the types of density property requested by the user and initializes the data arrays
        check = np.zeros(3, dtype=int)
        if 'm' in which_prop:
            check[0] = 1
            self.dens_m = np.zeros((nrow, ncol, 3), dtype=float)
        if 'j' in which_prop:
            check[1] = 1
            self.dens_j = np.zeros((nrow, ncol, 3), dtype=float)
        if 'J' in which_prop:
            check[2] = 1
            self.dens_JX = np.zeros((nrow, ncol, 3), dtype=float)
            self.dens_JY = np.zeros((nrow, ncol, 3), dtype=float)
            self.dens_JZ = np.zeros((nrow, ncol, 3), dtype=float)
        if (not check[0]) and (not check[1]) and (not check[2]):
            print('Error: Invalid Entry. Only the m, j, and J charachters are supported')
            sys.exit(1)

        # Gathers the data
        iamhere = 0

        if check[0]:
            iamhere = 3
            r = 0
            s = 0
            for i in range(0, blines):
                for j in range(0, len(data[i+iamhere].split())):
                    self.dens_m[r, s, 0] = data[i+iamhere].split()[j]
                    self.dens_m[r, s, 1] = data[i +
                                                iamhere+blines+skip].split()[j]
                    self.dens_m[r, s, 2] = data[i+iamhere +
                                                (2*blines)+(2*skip)].split()[j]
                    if s == (ncol - 1):
                        r += 1
                        s = 0
                    else:
                        s += 1
            iamhere = iamhere + 3*blines + 2*skip
        if check[1]:
            if iamhere == 0:
                iamhere = 3
            else:
                iamhere = iamhere + skip
            r = 0
            s = 0
            for i in range(0, blines):
                for j in range(0, len(data[i+iamhere].split())):
                    self.dens_j[r, s, 0] = data[i+iamhere].split()[j]
                    self.dens_j[r, s, 1] = data[i +
                                                iamhere+blines+skip].split()[j]
                    self.dens_j[r, s, 2] = data[i +
                                                iamhere+2*blines+2*skip].split()[j]
                    if s == (ncol - 1):
                        r += 1
                        s = 0
                    else:
                        s += 1
            iamhere = iamhere + 3*blines + 2*skip
        if check[2]:
            if iamhere == 0:
                iamhere = 3
            else:
                iamhere = iamhere + skip
            r = 0
            s = 0
            for i in range(0, blines):
                for j in range(0, len(data[i+iamhere].split())):
                    self.dens_JX[r, s, 0] = data[i+iamhere].split()[j]
                    self.dens_JX[r, s, 1] = data[i +
                                                 iamhere+blines+skip].split()[j]
                    self.dens_JX[r, s, 2] = data[i+iamhere +
                                                 (2*blines)+(2*skip)].split()[j]
                    self.dens_JY[r, s, 0] = data[i+iamhere +
                                                 (3*blines)+(3*skip)].split()[j]
                    self.dens_JY[r, s, 1] = data[i+iamhere +
                                                 (4*blines)+(4*skip)].split()[j]
                    self.dens_JY[r, s, 2] = data[i+iamhere +
                                                 (5*blines)+(5*skip)].split()[j]
                    self.dens_JZ[r, s, 0] = data[i+iamhere +
                                                 (6*blines)+(6*skip)].split()[j]
                    self.dens_JZ[r, s, 1] = data[i+iamhere +
                                                 (7*blines)+(7*skip)].split()[j]
                    self.dens_JZ[r, s, 2] = data[i+iamhere +
                                                 (8*blines)+(8*skip)].split()[j]
                    if s == (ncol - 1):
                        r += 1
                        s = 0
                    else:
                        s += 1
        return self

    def read_cry_bands(self, properties_output):
        """
        Deprecated.
        """
        import warnings

        warnings.warn('Deprecated. Use read_electron_band instead.')
        return self.read_electron_band(properties_output)

    def read_electron_band(self, properties_output):
        """
        Generate bands object from CRYSTAL BAND.DAT or fort.25 file.
        Energy unit: eV.

        Args:
            properties_output (str): File name

        Returns:
            self.bands (BandsBASE): A Bands base object
        """
        from CRYSTALpytools.base.propout import BandsBASE

        self.read_file(properties_output)
        if '-%-' in self.data[0]: #fort.25 file format
            self.bands = BandsBASE.f25_parser(self.data)
        else: #BAND.DAT file format
            self.bands = BandsBASE.BAND_parser(self.data)

        return self.bands

    def read_cry_doss(self, properties_output):
        """
        Deprecated.
        """
        import warnings

        warnings.warn('Deprecated. Use read_electron_dos instead.')
        return self.read_electron_dos(properties_output)

    def read_electron_dos(self, properties_output):
        """
        Generate doss object from CRYSTAL DOSS.DAT or fort.25 file.
        Energy unit: eV.

        Args:
            properties_output (str): File name

        Returns:
            self.doss (DOSBASE): A DOS base object
        """
        from CRYSTALpytools.base.propout import DOSBASE

        self.read_file(properties_output)
        if '-%-' in self.data[0]: #fort.25 file format
            self.doss = DOSBASE.f25_parser(self.data)
        else: #DOSS.DAT file format
            self.doss = DOSBASE.DOSS_parser(self.data)

        return self.doss

    def read_cry_contour(self, properties_output):
        """Read the CRYSTAL contour files to create the contour objects.
        
        Args:
            properties_output (str): The properties output file.
        Returns:
            Properties_output: The updated Properties_output object.
        """
        import sys
        import re
        import pandas as pd
        import numpy as np

        self.read_file(properties_output)

        filename = str(properties_output)

        tipo = ''

        if (filename.endswith('.SURFRHOO')):
            self.tipo = 'SURFRHOO'
            self.path = filename
        elif (filename.endswith('.SURFLAPP')):
            self.tipo = 'SURFLAPP'
            self.path = filename
        elif (filename.endswith('.SURFLAPM')):
            self.tipo = 'SURFLAPM'
            self.path = filename
        elif (filename.endswith('.SURFGRHO')):
            self.tipo = 'SURFGRHO'
            self.path = filename
        elif (filename.endswith('.SURFELFB')):
            self.tipo = 'SURFELFB'
            self.path = filename
        elif (filename.endswith('.SURFVIRI')):
            self.tipo = 'SURFVIRI'
            self.path = filename
        elif (filename.endswith('.SURFGKIN')):
            self.tipo = 'SURFGKIN'
            self.path = filename
        elif (filename.endswith('.SURFKKIN')):
            self.tipo = 'SURFKKIN'
            self.path = filename
        else:
            sys.exit('Please choose a valid file')

        l_dens = self.data

        n_punti_x = int(l_dens[1].strip().split()[0])
        n_punti_y = int(l_dens[1].strip().split()[1])

        self.npx = n_punti_x

        x_min = units.au_to_angstrom(float(l_dens[2].strip().split()[0]))
        x_max = units.au_to_angstrom(float(l_dens[2].strip().split()[1]))
        x_step = units.au_to_angstrom(float(l_dens[2].strip().split()[2]))

        y_min = units.au_to_angstrom(float(l_dens[3].strip().split()[0]))
        y_max = units.au_to_angstrom(float(l_dens[3].strip().split()[1]))
        y_step = units.au_to_angstrom(float(l_dens[3].strip().split()[2]))

        l_dens = l_dens[5:]

        m_dens = []
        for i in l_dens:
            m_dens.append(re.sub("\s\s+", " ", i))

        n_dens = []
        for i in m_dens:
            n_dens.append(i.replace('\n', '').split())

        self.df = pd.DataFrame(n_dens)

        self.x_points = np.linspace(x_min, x_max, n_punti_x)
        self.y_points = np.linspace(y_min, y_max, n_punti_y)

        a = x_max - x_min
        b = y_max - y_min
        r = a/b

        self.x_graph_param = 10
        self.y_graph_param = 10 / r

        ctr1 = np.array([0.002, 0.004, 0.008, 0.02, 0.04,
                         0.08, 0.2, 0.4, 0.8, 2, 4, 8, 20])
        colors1 = ['r', 'r', 'r', 'r', 'r', 'r',
                   'r', 'r', 'r', 'r', 'r', 'r', 'r']
        ls1 = ['-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-']

        ctr2 = np.array([-8, -4, -2, -0.8, -0.4, -0.2, -0.08, -0.04, -0.02, -0.008, -0.004, -0.002, 0.002, 0.004, 0.008, 0.02, 0.04, 0.08,
                         0.2, 0.4, 0.8, 2, 4, 8])
        colors2 = ['b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b',
                   'b', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r']
        ls2 = ['--', '--', '--', '--', '--', '--', '--', '--', '--', '--', '--',
               '--', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-']

        ctr3 = np.array([0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90,
                         0.95, 1])
        colors3 = ['k', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b', 'b',
                   'b', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r', 'r']
        ls3 = ['dotted', '--', '--', '--', '--', '--', '--', '--', '--',
               '--', '--', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-']

        if (self.tipo == 'SURFRHOO') or (self.tipo == 'SURFGRHO') or (self.tipo == 'SURFGKIN'):
            self.levels = ctr1
            self.colors = colors1
            self.linestyles = ls1
            self.fmt = '%1.3f'
        elif (self.tipo == 'SURFLAPP') or (self.tipo == 'SURFLAPM') or (self.tipo == 'SURFVIRI') or (self.tipo == 'SURFKKIN'):
            self.levels = ctr2
            self.colors = colors2
            self.linestyles = ls2
            self.fmt = '%1.3f'
        elif (self.tipo == 'SURFELFB'):
            self.levels = ctr3
            self.colors = colors3
            self.linestyles = ls3
            self.fmt = '%1.2f'

        return self

    def read_cry_xrd_spec(self, properties_output):
        """
        Read XRD spectrum data from a file.
        
        Args:
            properties_output (str): Path to the properties output file.
        Returns:
            self: The modified object with extracted XRD spectrum data.
        """
        import sys
        import re
        import pandas as pd

        self.read_file(properties_output)

        data = self.data
        filename = self.abspath
        title = self.title

        if filename.endswith('.outp'):
            pass
        else:
            sys.exit('please, choose a valid file or rename it properly')

        spectrum = re.compile(
            '2THETA    INTENS  INTENS-LP INTENS-LP-DW', re.DOTALL)

        match = []

        a = 0

        for line in data:
            if spectrum.search(line):
                match.append('WRITE LINE:' + line)
                a = 1
            else:
                match.append('WRONG LINE:' + line)

        if (a == 0):
            sys.exit('please, choose a valid file or rename it properly')

        df = pd.DataFrame(match)

        num_riga = (df[df[0].str.contains(u'WRITE')].index.values)

        num_riga = num_riga[0]

        match = match[num_riga:]

        pattern = re.compile(
            '\s+ \d+\.\d+ \s+ \d+\.\d+ \s+ \d+\.\d+ \s+ \d+\.\d+\n', re.DOTALL)

        match_2 = []

        for line in match:
            if pattern.search(line):
                # pulisco dalle scritte di prima
                line = line.replace('WRONG LINE:', '')
                match_2.append(line)

        df = pd.DataFrame([i.strip().split() for i in match_2])

        for i in range(0, 4):
            df[i] = df[i].astype(float)

        df = df.rename(columns={0: '2THETA', 1: 'INTENS',
                                2: 'INTENS-LP', 3: 'INTENS-LP-DW'})

        self.x = df['2THETA']
        self.y = df['INTENS-LP']

        self.title = title[:-1]

        return self

    def read_cry_rholine(self, properties_output):
        """
        Read density line data from a file.
        
        Args:
            properties_output (str): Path to the properties output file.
        Returns:
            self: The modified object with extracted density line data.
        """
        import sys
        import re
        import pandas as pd

        self.read_file(properties_output)

        l_dens = self.data
        filename = self.abspath
        title = self.title

        if filename.endswith('.RHOLINE'):
            pass
        else:
            sys.exit('please, choose a valid file or rename it properly')

        m_dens = []
        for i in l_dens:
            m_dens.append(re.sub("\s\s+", " ", i))

        n_dens = []
        for i in m_dens:
            n_dens.append(i.replace('\n', '').split())

        df_dens = pd.DataFrame(n_dens)
        df_dens = df_dens.dropna()

        for i in range(0, len(df_dens.columns)):
            df_dens[i] = pd.to_numeric(df_dens[i])

        self.x = units.au_to_angstrom((df_dens[0]-5.55))
        self.y = df_dens[1]/0.148184743

        self.title = title[:-4]

        return self

    def read_cry_seebeck(self, properties_output):
        """
        Read Seebeck coefficient data from a file.
        
        Args:
            properties_output (str): Path to the properties output file.
        Returns:
            self: The modified object with extracted Seebeck coefficient data.
        """
        import sys
        import re
        import pandas as pd

        self.read_file(properties_output)

        data = self.data
        filename = self.abspath
        title = self.title

        spectrum = re.compile('Npoints', re.DOTALL)

        match = []

        for line in data:
            if spectrum.search(line):
                match.append('RIGHT LINE:' + line)
            else:
                match.append('WRONG LINE:' + line)

        df = pd.DataFrame(match)
        indx = list(df[df[0].str.contains("RIGHT")].index)

        lin = []
        for i in indx:
            lin.append(i+1)

        diffs = [abs(x - y) for x, y in zip(lin, lin[1:])]

        length = diffs[0] - 1

        lif = []
        for i in lin:
            lif.append(i+length)

        c = []
        for i in range(len(lin)):
            c.append(lin[i])
            c.append(lif[i])

        d = [c[i:i + 2] for i in range(0, len(c), 2)]

        l = []
        for i in range(0, len(d)):
            pd.DataFrame(l.append(df[d[i][0]:d[i][1]]))

        right = df[df[0].str.contains("RIGHT")]
        right = right.reset_index().drop('index', axis=1)

        self.temp = []

        for i in range(0, len(right)):
            self.temp.append(float(str(right[0][i])[20:24]))

        ll = []
        for k in range(0, len(l)):
            ll.append(l[k].reset_index().drop('index', axis=1))

        self.all_data = []
        for k in range(0, len(ll)):
            for i in ll[k]:
                self.all_data.append(ll[k][i].apply(
                    lambda x: x.replace('WRONG LINE:', '')))

        self.volume = (float(str(match[2:3])[-13:-4]))

        self.title = title

        return self

    def read_cry_sigma(self, properties_output):
        """
        Read electrical conductivity data from a file.
        
        Args:
            properties_output (str): Path to the properties output file.
        Returns:
            self: The modified object with extracted electrical conductivity data.
        """
        import sys
        import re
        import pandas as pd

        self.read_file(properties_output)

        data = self.data
        filename = self.abspath
        title = self.title

        spectrum = re.compile('Npoints', re.DOTALL)

        match = []

        for line in data:
            if spectrum.search(line):
                match.append('RIGHT LINE:' + line)
            else:
                match.append('WRONG LINE:' + line)

        df = pd.DataFrame(match)
        indx = list(df[df[0].str.contains("RIGHT")].index)

        lin = []
        for i in indx:
            lin.append(i+1)

        diffs = [abs(x - y) for x, y in zip(lin, lin[1:])]

        length = diffs[0] - 1

        lif = []
        for i in lin:
            lif.append(i+length)

        c = []
        for i in range(len(lin)):
            c.append(lin[i])
            c.append(lif[i])

        d = [c[i:i + 2] for i in range(0, len(c), 2)]

        l = []
        for i in range(0, len(d)):
            pd.DataFrame(l.append(df[d[i][0]:d[i][1]]))

        right = df[df[0].str.contains("RIGHT")]
        right = right.reset_index().drop('index', axis=1)

        self.temp = []

        for i in range(0, len(right)):
            self.temp.append(float(str(right[0][i])[20:24]))

        ll = []
        for k in range(0, len(l)):
            ll.append(l[k].reset_index().drop('index', axis=1))

        self.all_data = []
        for k in range(0, len(ll)):
            for i in ll[k]:
                self.all_data.append(ll[k][i].apply(
                    lambda x: x.replace('WRONG LINE:', '')))

        self.volume = (float(str(match[2:3])[-13:-4]))

        self.title = title

        return self

    def read_cry_lapl_profile(self, properties_output):
        """
        Read Laplacian profile data from a file.
        
        Args:
            properties_output (str): Path to the properties output file.
        Returns:
            self: The modified object with extracted Laplacian profile data.
        """
        import pandas as pd
        import re
        import numpy as np

        data = self.data
        filename = self.abspath
        title = self.title

        self.read_file(properties_output)

        spectrum = re.compile('PROFILE ALONG THE POINTS', re.DOTALL)

        match = []

        for line in data:
            if spectrum.search(line):
                match.append('RIGHT LINE: ' + line)
            else:
                match.append('WRONG LINE: ' + line)

        df = pd.DataFrame(match)
        num_riga = (df[df[0].str.contains(u'RIGHT')].index.values)
        num_in = num_riga + 8

        spectrum_fin = re.compile('EEEEEEEEEE TERMINATION  DATE', re.DOTALL)

        match_fin = []

        for line in data:
            if spectrum_fin.search(line):
                match_fin.append('RIGHT LINE: ' + line)
            else:
                match_fin.append('WRONG LINE: ' + line)

        df_fin = pd.DataFrame(match_fin)

        num_fin = (df_fin[df_fin[0].str.contains(u'RIGHT')].index.values)
        match = match[num_in[0]:num_fin[0]-2]

        match_2 = []
        for line in match:
            line = line.replace('WRONG LINE:', '')
            match_2.append(line)

        df = pd.DataFrame([i.strip().split() for i in match_2])
        df = df.rename({0: 'x', 1: 'y', 2: 'z', 3: 'dist',
                        4: 'rho', 5: 'lapl', 6: 'L3', 7: 'ellip'}, axis=1)
        df = df.drop(df[df.lapl == '********'].index)
        df = df.reset_index().drop('index', axis=1)
        df['lapl'] = df['lapl'].apply(pd.to_numeric)
        df['dist'] = df['dist'].apply(pd.to_numeric)
        self.datax = df.dist
        self.datay = df.lapl

        return self

    def read_cry_density_profile(self, properties_output):
        """
        Read density profile data from a file.
        
        Args:
            properties_output (str): Path to the properties output file.
        Returns:
            self: The modified object with extracted density profile data.
        """
        import pandas as pd
        import re
        import numpy as np

        self.read_file(properties_output)

        data = self.data
        filename = self.abspath
        title = self.title

        spectrum = re.compile('PROFILE ALONG THE POINTS', re.DOTALL)

        match = []

        for line in data:
            if spectrum.search(line):
                match.append('RIGHT LINE: ' + line)
            else:
                match.append('WRONG LINE: ' + line)

        df = pd.DataFrame(match)
        num_riga = (df[df[0].str.contains(u'RIGHT')].index.values)
        num_in = num_riga + 8

        spectrum_fin = re.compile('EEEEEEEEEE TERMINATION  DATE', re.DOTALL)

        match_fin = []

        for line in data:
            if spectrum_fin.search(line):
                match_fin.append('RIGHT LINE: ' + line)
            else:
                match_fin.append('WRONG LINE: ' + line)

        df_fin = pd.DataFrame(match_fin)

        num_fin = (df_fin[df_fin[0].str.contains(u'RIGHT')].index.values)
        match = match[num_in[0]:num_fin[0]-2]

        match_2 = []
        for line in match:
            line = line.replace('WRONG LINE:', '')
            match_2.append(line)

        df = pd.DataFrame([i.strip().split() for i in match_2])
        df = df.rename({0: 'x', 1: 'y', 2: 'z', 3: 'dist',
                        4: 'rho', 5: 'lapl', 6: 'L3', 7: 'ellip'}, axis=1)
        df = df.drop(df[df.lapl == '********'].index)
        df = df.reset_index().drop('index', axis=1)
        df['rho'] = df['rho'].apply(pd.to_numeric)
        df['dist'] = df['dist'].apply(pd.to_numeric)
        self.datax = df.dist
        self.datay = df.rho

        return self


class Crystal_gui:
    """
    This class can read a CRYSTAL gui file into an object or substrate
    information of the object to generate a gui file.
    """
    def __init__(self):
        pass

    def read_gui(self, gui_file):
        """
        This is used mainly to convert the object into an ASE or pymatgen
        object.

        Args:
            gui_file (str): The CRYSTAL structure (gui) file
        """
        try:
            if gui_file[-3:] != 'gui' and gui_file[-3:] != 'f34' and 'optc' not in gui_file:
                gui_file = gui_file + '.gui'
            file = open(gui_file, 'r')
            data = file.readlines()
            file.close()
        except:
            raise FileNotFoundError('A .gui file needs to be specified')

        self.dimensionality = int(data[0].split()[0])
        self.lattice = []
        self.symmops = []
        for i in range(1, 4):
            self.lattice.append([float(x) for x in data[i].split()])
        self.n_symmops = int(data[4].split()[0])
        for i in range(5, 5+self.n_symmops*4):
            self.symmops.append([float(x) for x in data[i].split()])
        self.n_atoms = int(data[5+self.n_symmops*4].split()[0])
        self.atom_number = []
        self.atom_positions = []
        for i in range(6+self.n_symmops*4, 6+self.n_symmops*4+self.n_atoms):
            atom_line = data[i].split()
            self.atom_number.append(str(atom_line[0]))
            self.atom_positions.append([float(x) for x in atom_line[1:]])
        self.space_group = int(data[-1].split()[0])

        return self

    def write_gui(self, gui_file, symm=True, pseudo_atoms=[]):
        """
        Write a CRYSTAL gui file (to file)

        Args:
            gui_file (str): The name of the gui that is going to be written (
                including .gui).
            symm (bool): Whether to include symmetry operations.
            pseudo_atoms (list[int]): A list of atoms whose core is described
                by a pseudopotential
        """
        import numpy as np

        with open(gui_file, 'w') as file:

            # First line
            file.writelines('%4s   1   1\n' % self.dimensionality)
            # Cell vectors
            for vector in self.lattice:
                file.writelines('{}\n'.format(
                    ''.join(['{0: 20.12E}'.format(np.round(n, 12)) for n in vector])
                ))
            # N symm ops
            file.writelines('{:5d}\n'.format(self.n_symmops))

            # symm ops
            for symmops in self.symmops:
                file.writelines('{}\n'.format(
                    ''.join(['{0: 20.12f}'.format(np.round(n, 12)) for n in symmops])
                ))
            # N atoms
            file.writelines('{:5d}\n'.format(self.n_atoms))

            # atom number (including pseudopotentials) + coordinates cart
            for i in range(self.n_atoms):
                if self.atom_number[i] in pseudo_atoms:
                    file.writelines('{:5d}{}\n'.format(
                        int(self.atom_number[i])+200,
                        ''.join(['{0: 20.12E}'.format(np.round(x, 12)) for x in self.atom_positions[i]])
                    ))
                else:
                    file.writelines('{:5d}{}\n'.format(
                        int(self.atom_number[i]),
                        ''.join(['{0: 20.12E}'.format(np.round(x, 12)) for x in self.atom_positions[i]])
                    ))

            # space group + n symm ops
            if symm == True:
                file.writelines('{:5d}{:5d}\n'.format(
                    self.space_group, self.n_symmops
                ))
            else:
                file.writelines('{:5d}{:5d}\n'.format(1, 1))

        file.close()


class Crystal_density():
    """
    Read density data from a .f98 file.
    """

    def __init__(self):

        pass

    def read_cry_irr_density(self, fort98_unit):
        """
        Read density profile data from a CRYSTAL .f98 file.
        Args:
            fort98_unit (str): The file containing the formatted density matrix.
        Returns:
            None
        Note:
        This is a work in progress. If you are interested in this functionality,
        please open an Issue on GitHub.
        """
        self.file_name = fort98_unit
        self.is_irr = True

        import sys
        import numpy as np
        import re

        try:
            file = open(self.file_name, 'r')
            data = file.readlines()
            file.close()
        except:
            print('EXITING: a CRYSTAL .f98 file needs to be specified')
            sys.exit(1)

        self.all_file = data

        # the keyword BASATO appears twice, this is a check to see which basato
        # is being read
        basato1 = False

        for i, line in enumerate(data):

            if re.match(r'^LIMINF LIMTOL LIMPAR', line):
                inf_vec_len, tol_vec_len, par_vec_len = [
                    int(x) for x in data[i+1].split()]

            elif re.match(r'^INF', line):
                self.inf_vec = []
                inf_n_lines = int(np.ceil(inf_vec_len/8))
                for j in range(inf_n_lines):
                    self.inf_vec.extend([int(x) for x in data[i+1+j].split()])
                n_symmops = self.inf_vec[0]
                n_atoms = self.inf_vec[23]
                n_shells = self.inf_vec[19]
                '''if self.inf_vec[26] == 0:
                    self.spin_pol == False
                elif self.inf_vec[26] == 1:
                    self.spin_pol == True'''
                n_prim_gto = self.inf_vec[74]
                f_irr_len = (self.inf_vec[63]+1)*self.inf_vec[227]
                p_irr_len = (self.inf_vec[63]+1)*self.inf_vec[18]
                nnnc_len = self.inf_vec[190]
                la3_len = self.inf_vec[55]
                # n_symmops_noinv = inf_vec[1]

            elif re.match(r'^TOL', line):
                self.tol_vec = []
                tol_n_lines = int(np.ceil(tol_vec_len/8))
                for j in range(tol_n_lines):
                    self.tol_vec.extend([int(x) for x in data[i+1+j].split()])

            elif re.match(r'^PAR', line):
                self.par_vec = []
                par_n_lines = int(np.ceil(par_vec_len/4))
                for j in range(par_n_lines):
                    # The negative elements appear connected to the previous one
                    # eg:  0.0000000000000E+00-1.0000000000000E+00
                    # The line below fixes that issue
                    for item in range(0, int(len(data[i+1+j])/20)):
                        self.par_vec.append(
                            float(data[i+1+j][(item)*20:(item+1)*20]))

            elif re.match(r'^XYVGVE', line):
                # This vector contains the rotations, translation,
                # lattice vectors and transformation matrix from primitive to
                # crystallographic cell
                # Read all of it first and separate later
                xyvgve_n_lines = int(np.ceil((n_symmops*12+18)/4))
                xyvgve_vec = []
                for j in range(xyvgve_n_lines):
                    # The negative elements appear connected to the previous one
                    # eg:  0.0000000000000E+00-1.0000000000000E+00
                    # The line below fixes that issue
                    for item in range(0, int(len(data[i+1+j])/20)):
                        xyvgve_vec.append(
                            float(data[i+1+j][(item)*20:(item+1)*20]))
                # Now let's split the xyvgve_vec
                self.rotations_vec = xyvgve_vec[0:n_symmops*9]
                self.translations_vec = xyvgve_vec[n_symmops *
                                                   9:n_symmops*9+n_symmops*3]
                self.direct_lattice_vec = xyvgve_vec[n_symmops *
                                                     12:n_symmops*12+9]
                self.transf_matrix = xyvgve_vec[-9:]

            elif re.match(r'^BASATO', line):
                if basato1 == False:
                    basato_n_lines = int(
                        np.ceil((n_atoms*4+n_shells*5+n_prim_gto*7)/4))
                    basato_vec = []
                    for j in range(basato_n_lines):
                        # The negative elements appear connected to the previous one
                        # eg:  0.0000000000000E+00-1.0000000000000E+00
                        # The line below fixes that issue
                        for item in range(0, int(len(data[i+1+j])/20)):
                            basato_vec.append(
                                float(data[i+1+j][(item)*20:(item+1)*20]))
                    # Extract the iformation we need from basato

                    # Atom coordinates
                    self.atom_coord = []
                    for j in range(0, 3*n_atoms, 3):
                        self.atom_coord.append(
                            basato_vec[(n_atoms+j):(n_atoms+j+3)])
                    # self.atom_coord = np.array(self.atom_coord)

                    # Assign the shell to the atom
                    self.shell_coord = []
                    # The beginning of the part of BASATO I need here
                    init = 4*n_atoms + 2*n_shells
                    for j in range(0, 3*n_shells, 3):
                        self.shell_coord.append(
                            basato_vec[(init+j):(init+j+3)])
                    # self.shell_coord = np.array(self.shell_coord)

                    # Array that defines which atom a shell belongs to
                    self.shell_to_atom = []
                    for coord in self.shell_coord:
                        self.shell_to_atom.append(self.atom_coord.index(coord))
                    basato1 = True

                elif basato1 == True:
                    self.basato2 = []
                    j = i + 1
                    while 'SPINOR' not in data[j].split()[0]:
                        # The negative elements appear connected to the previous one
                        # eg:  0.0000000000000E+00-1.0000000000000E+00
                        # As opposite to the loops above where the float read was 20
                        # characters long, this ones are 21
                        # The line below fixes that issue
                        self.basato2.extend([int(x) for x in data[j].split()])
                        j += 1
                    self.atom_shell = self.basato2[-n_shells:]

            elif re.match(r'^SPINOR', line):
                self.f_irr = []
                self.charges = []
                # self.spin = [0]*(2*n_atoms) #tmp
                self.spin = []
                self.ghost = []
                n_ghost = 0
                n_spin_lines = int(np.ceil((n_atoms*2)/8))
                n_basold = 0
                if 'BASOLD' in data[i+n_spin_lines+1]:
                    n_basold = 9 + 3 * \
                        self.inf_vec[1] + n_shells + 3*n_atoms+3 * \
                        n_shells+self.inf_vec[4]+1+3*self.inf_vec[78]
                n_basold_lines = int(np.ceil((n_basold)/4))
                n_charge_lines = int(np.ceil(n_atoms/4))
                skip = n_spin_lines + n_charge_lines + 1 + n_basold_lines
                for j in range(n_spin_lines):
                    self.spin.extend([int(x) for x in data[i + j + 1].split()])
                if 'IGHOST' in data[i+n_spin_lines+1]:
                    n_ghost = int(np.ceil((n_atoms)/8)) + 1
                    skip = skip + n_ghost
                    for j in range(n_ghost-1):
                        self.ghost.extend(
                            [float(x) for x in data[i + j + n_spin_lines + 2].split()])
                f_irr_n_lines = int(np.ceil(f_irr_len/4))
                for j in range(n_charge_lines):
                    self.charges.extend(
                        [float(x) for x in data[i+j+n_spin_lines+n_basold+n_ghost+1].split()])
                for j in range(f_irr_n_lines):
                    # The negative elements appear connected to the previous one
                    # eg:  0.0000000000000E+00-1.0000000000000E+00
                    # As opposite to the loops above where the float read was 20
                    # characters long, this ones are 21
                    # The line below fixes that issue
                    for item in range(0, int(len(data[i+skip+j])/21)):
                        self.f_irr.append(
                            float(data[i+skip+j][(item)*21:(item+1)*21]))
                self.p_irr = []
                p_irr_n_lines = int(np.ceil(p_irr_len/4))
                skip += 1
                for k in range(i+skip+j, i+skip+j+p_irr_n_lines):
                    # The negative elements appear connected to the previous one
                    # eg:  0.0000000000000E+00-1.0000000000000E+00
                    # As opposite to the loops above where the float read was 20
                    # characters long, this ones are 21
                    # The line below fixes that issue
                    for item in range(0, int(len(data[k])/21)):
                        self.p_irr.append(
                            float(data[k][(item)*21:(item+1)*21]))

            elif re.match(r'^   NCF', line):
                # The ncf vector contains the pointers to the symmetry irerducible
                # shell couples la3, la4
                self.ncf = []
                j = i+1
                while 'NSTATG' not in data[j].split()[0]:
                    # The negative elements appear connected to the previous one
                    # eg:  0.0000000000000E+00-1.0000000000000E+00
                    # As opposite to the loops above where the float read was 20
                    # characters long, this ones are 21
                    # The line below fixes that issue
                    self.ncf.extend([int(x) for x in data[j].split()])
                    j += 1

            elif re.match(r'^NSTATG', line):
                # The nstatg vector contains the pointers to the starting point
                # of each couple set in P_irr and F_irr
                self.nstatg = []
                j = i+1
                while 'NSTAFG' not in data[j].split()[0]:
                    # The negative elements appear connected to the previous one
                    # eg:  0.0000000000000E+00-1.0000000000000E+00
                    # As opposite to the loops above where the float read was 20
                    # characters long, this ones are 21
                    # The line below fixes that issue
                    self.nstatg.extend([int(x) for x in data[j].split()])
                    j += 1

            elif re.match(r'^  NNNC', line):
                # The nnnc points the starting position in the P matrix for
                # each couple, and its size corresponds to the total number
                # of shell couple in the shell couple sets
                self.nnnc = []
                nnnc_n_lines = int(np.ceil(nnnc_len/8))
                for j in range(nnnc_n_lines):
                    # The negative elements appear connected to the previous one
                    # eg:  0.0000000000000E+00-1.0000000000000E+00
                    # As opposite to the loops above where the float read was 20
                    # characters long, this ones are 21
                    # The line below fixes that issue
                    for item in range(0, int(len(data[i+1+j])/10)):
                        self.nnnc.append(
                            int(data[i+1+j][(item)*10:(item+1)*10]))
            elif re.match(r'^   LA3', line):
                # The nnnc points the starting position in the P matrix for
                # each couple, and its size corresponds to the total number
                # of shell couple in the shell couple sets
                self.la3 = []
                # nnnc_n_lines = int(np.ceil(nnnc_len/8))
                j = i+1
                while 'LA4' not in data[j].split()[0]:
                    # The negative elements appear connected to the previous one
                    # eg:  0.0000000000000E+00-1.0000000000000E+00
                    # As opposite to the loops above where the float read was 20
                    # characters long, this ones are 21
                    # The line below fixes that issue
                    self.la3.extend([int(x) for x in data[j].split()])
                    j += 1
            elif re.match(r'^   LA4', line):
                # The nnnc points the starting position in the P matrix for
                # each couple, and its size corresponds to the total number
                # of shell couple in the shell couple sets
                self.la4 = []
                # nnnc_n_lines = int(np.ceil(nnnc_len/8))
                j = i+1
                while 'IROF' not in data[j].split()[0]:
                    # The negative elements appear connected to the previous one
                    # eg:  0.0000000000000E+00-1.0000000000000E+00
                    # As opposite to the loops above where the float read was 20
                    # characters long, this ones are 21
                    # The line below fixes that issue
                    self.la4.extend([int(x) for x in data[j].split()])
                    j += 1


def cry_combine_density(density1, density2, density3, new_density='new_density.f98', spin_pol=False):
    """
    Combine density matrix files.
    
    Args:
        density1 (str): The first density matrix file.
        density2 (str): The second density matrix file.
        density3 (str): The density matrix file for the whole system.
        new_density (str, optional): The name of the new density matrix. Defaults to 'new_density.f98'.
        spin_pol (bool, optional): Specifies if the system is spin polarized. Defaults to False.
    Returns:
        None
    Note:
        This is a work in progress. If you are interested in this functionality,
        please open an Issue on GitHub.
    """

    import sys
    import numpy as np

    try:
        density1_data = Crystal_density(density1)  # substrate
        density2_data = Crystal_density(density2)  # adsorbate

        density3_data_obj = Crystal_density(density3)
        density3_data = density3_data_obj.all_file
    except:
        print('EXITING: a CRYSTAL .f98 file needs to be specified')
        sys.exit(1)

    # Find P_irr <-> atom correspondence
    fragment_1 = []
    fragment_2 = []

    for i, j in enumerate(density1_data.ncf):
        # density1_data.la3[j] is the shell number
        # density1_data.atom_shell[density1_data.la3[j]] is the atom position number (1-6)
        # density1_data.ghost[density1_data.atom_shell[density1_data.la3[j]]] is either 0 or atomic number depending on ghost or not
        # This tells me if the shell belongs to this fragment
        n_elements = density1_data.nstatg[i] - density1_data.nstatg[i - 1]

        if density1_data.ghost[density1_data.atom_shell[density1_data.la3[j-1]-1]-1] == 0 and \
                density1_data.ghost[density1_data.atom_shell[density1_data.la4[j-1]-1]-1] == 0:
            fragment_1.extend([True]*n_elements)
        else:
            fragment_1.extend([False]*n_elements)

        if density1_data.ghost[density1_data.atom_shell[density1_data.la3[j-1]-1]-1] != 0 and \
                density1_data.ghost[density1_data.atom_shell[density1_data.la4[j-1]-1]-1] != 0:
            fragment_2.extend([True]*n_elements)
        else:
            fragment_2.extend([False]*n_elements)

    if spin_pol == True:
        spin_p1 = fragment_1.copy()
        spin_p2 = fragment_2.copy()
        fragment_1.extend(spin_p1)
        fragment_2.extend(spin_p2)

    beginning = density3_data.index('SPINOR\n')
    end = density3_data.index('   NCF\n')
    sum_density = (np.array(density1_data.p_irr) +
                   np.array(density2_data.p_irr))/2
    sum_fock = np.array(density1_data.f_irr)+np.array(density2_data.f_irr)
    sum_charges = np.array(density1_data.charges) + \
        np.array(density2_data.charges)
    spinor = ['SPINOR\n']
    charges = []
    fock = []
    density = []
    new_fock = sum_fock  # TMP
    new_fock = [0] * len(density3_data_obj.f_irr)
    new_p = []

    for i in range(len(fragment_1)):
        if fragment_1[i] == True and fragment_2[i] == False:
            # new_fock.append(density1_data.f_irr[i])
            new_p.append(density1_data.p_irr[i])
        elif fragment_1[i] == False and fragment_2[i] == True:
            # new_fock.append(density2_data.f_irr[i])
            new_p.append(density2_data.p_irr[i])
        elif fragment_1[i] == False and fragment_2[i] == False:
            # new_fock.append(0.)
            new_p.append(sum_density[i])
            # new_p.append(0.)
            # new_p.append(density3_data_obj.p_irr[i])

    for i in range(0, len(density3_data_obj.spin), 8):
        spinor.append(' '.join([str(x)
                                for x in density3_data_obj.spin[i:i+8]])+'\n')
    for i in range(0, len(sum_charges), 4):
        charges.append(' '.join(["{:.13e}".format(x)
                                 for x in sum_charges[i:i+4]])+'\n')
    for i in range(0, len(new_fock), 4):
        fock.append(' '.join(["{:.13e}".format(x)
                              for x in new_fock[i:i+4]])+'\n')
    for i in range(0, len(new_p), 4):
        density.append(' '.join(["{:.13e}".format(x)
                                 for x in new_p[i:i+4]])+'\n')

    final_fort98 = density3_data[0:beginning] + \
        spinor+charges+fock+density+density3_data[end:]
    with open(new_density, 'w') as file:
        for line in final_fort98:
            file.writelines(line)


def write_cry_density(fort98_name, new_p, new_fort98):
    """
    Write the formatted density matrix.
    
    Args:
        fort98_name (str): The name of the previous density matrix file.
        new_p (list): The new density matrix.
        new_fort98 (str): The name of the new density matrix file.
        
        Returns:
        None
    Note:
        This is a work in progress. If you are interested in this functionality,
        please open an Issue on GitHub.
    """

    import numpy as np

    file = open(fort98_name, 'r')
    data = file.readlines()
    file.close()

    density = Crystal_density(fort98_name)

    n_spin_lines = int(np.ceil((density.inf_vec[23] * 2) / 8))
    n_charges_lines = int(np.ceil((density.inf_vec[23]) / 4))
    beginning = data.index('SPINOR\n') + n_spin_lines + n_charges_lines + 1
    end = data.index('   NCF\n')

    new_fock_vect = [0] * len(density.f_irr)

    new_fock = []
    for i in range(0, len(new_fock_vect), 4):
        new_fock.append(' '.join(["{:.13e}".format(x)
                                  for x in new_fock_vect[i:i + 4]]) + '\n')

    new_density = []
    for i in range(0, len(new_p), 4):
        new_density.append(' '.join(["{:.13e}".format(x)
                                     for x in new_p[i:i+4]])+'\n')

    final_fort98 = data[0:beginning]+new_fock+new_density+data[end:]
    with open(new_fort98, 'w') as file:
        for line in final_fort98:
            file.writelines(line)
