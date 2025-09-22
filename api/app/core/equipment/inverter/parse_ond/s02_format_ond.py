from app.core.equipment._utils.enumerations import ONDformat


def convert_ond_data(
    *,
    inverter: dict,
    ond_format: ONDformat,
):
    """
    Convert OND format data to proximal format data, including raw efficiency curves.
    """
    result = {}
    match ond_format:
        case ONDformat.TEXT:
            pv_obj = inverter.get("PVObject_", {})
            converter = pv_obj.get("Converter", {})
            pv_commercial = pv_obj.get("PVObject_Commercial", {})

            # BOOK-KEEPING
            manufacturer = pv_commercial.get("Manufacturer")
            if manufacturer:
                result["manufacturer"] = manufacturer
            model = pv_commercial.get("Model")
            if model:
                result["model"] = model

            # OPERATING WINDOW
            vmpp_min = converter.get("VMppMin")
            if vmpp_min:
                result["voltage_mpp_min"] = float(vmpp_min)
                result["voltage_min"] = float(vmpp_min)  # Same as voltage_mpp_min
            vmpp_max = converter.get("VMPPMax")
            if vmpp_max:
                result["voltage_mpp_max"] = float(vmpp_max)
            vabs_max = converter.get("VAbsMax")
            if vabs_max:
                result["voltage_max"] = float(vabs_max)
            current_max = converter.get("IDCMax")
            if current_max:
                current_max = float(current_max)
                if current_max < 1:
                    result["current_max"] = -999
                else:
                    result["current_max"] = current_max
            # Power and temperature references
            pmaxout = converter.get("PMaxOUT")
            plim1 = converter.get("PLim1")
            if pmaxout and plim1:
                result["power_at_reference_temp"] = [float(pmaxout), float(plim1)]
            tpn = converter.get("TPNom")
            tplim1 = converter.get("TPLim1")
            if tpn and tplim1:
                result["reference_temp"] = [float(tpn), float(tplim1)]

            # Voltage and efficiency profiles
            vnom_eff = converter.get("VNomEff", "")
            vnom_list = [float(v.strip()) for v in vnom_eff.split(",") if v.strip()]
            result["voltage_nominal_efficiency"] = vnom_list

            # Extract raw efficiency curves from ProfilPIOVx
            profil_v_keys = ["ProfilPIOV1", "ProfilPIOV2", "ProfilPIOV3"]
            voltage_labels = ["low", "mid", "high"]

            for idx, (v_key, label) in enumerate(zip(profil_v_keys, voltage_labels)):
                if idx >= len(vnom_list):  # Ensure we don't exceed defined voltages
                    break

                profil = converter.get(v_key, {})
                n_pts_eff = int(profil.get("NPtsEff", 0))
                points = []

                for i in range(1, n_pts_eff + 1):
                    point_str = profil.get(f"Point_{i}", "0.0,0.0")
                    try:
                        dc_input_str, ac_output_str = point_str.split(",")
                        dc_input = float(dc_input_str.strip())
                        ac_output = float(ac_output_str.strip())
                        points.append((dc_input, ac_output))
                    except ValueError:
                        continue  # Skip invalid points

                if points:
                    result_key = f"efficiency_at_{label}_voltage"
                    result[result_key] = points

            # EFFICIENCY
            pnom_conv = converter.get("PNomConv")
            if pnom_conv:
                result["power_ac_nominal"] = float(pnom_conv) * 1_000
            max_efficiency = converter.get("EfficMax")
            if max_efficiency:
                max_efficiency = float(max_efficiency) / 100.0
                result["max_efficiency"] = max_efficiency

            # NIGHT LOSS
            night_loss = pv_obj.get("Night_Loss")
            if night_loss:
                result["night_tare"] = night_loss

        # --- Binary ---
        case ONDformat.BINARY:
            # BOOK-KEEPING
            manufacturer = inverter.get("Manufacturer")
            if manufacturer:
                result["manufacturer"] = manufacturer
            model = inverter.get("Model")
            if model:
                result["model"] = model

            # OPERATING WINDOW
            vmpp_min = inverter.get("VMppMin")
            if vmpp_min:
                result["voltage_mpp_min"] = float(vmpp_min)
                result["voltage_min"] = float(vmpp_min)  # Same as voltage_mpp_min
            vmpp_max = inverter.get("VMPPMax")
            if vmpp_max:
                result["voltage_mpp_max"] = float(vmpp_max)
            vabs_max = inverter.get("VAbsMax")
            if vabs_max:
                result["voltage_max"] = float(vabs_max)
            current_max = inverter.get("IMaxDC")
            if current_max:
                current_max = float(current_max)
                if current_max < 1:
                    result["current_max"] = -999
                else:
                    result["current_max"] = current_max

            # Power and temperature references
            pmax_out = inverter.get("PMaxOUT")
            if pmax_out:
                result["power_at_reference_temp"] = [float(pmax_out)]

            # EFFICIENCY
            pnom_ac = inverter.get("PNomAC")
            if pnom_ac:
                result["power_ac_nominal"] = float(pnom_ac)
            max_efficiency = inverter.get("EfficMax")
            if max_efficiency:
                max_efficiency = float(max_efficiency) / 100.0
                result["max_efficiency"] = max_efficiency

            # Extract efficiency curves from binary format
            # Map curve names to voltage labels
            curve_mappings = [
                ("LowVoltageEfficiencyCurve", "low"),
                ("MediumVoltageEfficiencyCurve", "mid"),
                ("HighVoltageEfficiencyCurve", "high"),
            ]

            # Also extract voltage levels for nominal efficiency
            voltage_levels = []
            low_v = inverter.get("LowVoltageLevel")
            if low_v and low_v > 0:
                voltage_levels.append(float(low_v))
            med_v = inverter.get("MediumVoltageLevel")
            if med_v and med_v > 0:
                voltage_levels.append(float(med_v))
            high_v = inverter.get("HighVoltageLevel")
            if high_v and high_v > 0:
                voltage_levels.append(float(high_v))

            if voltage_levels:
                result["voltage_nominal_efficiency"] = voltage_levels

            for curve_key, label in curve_mappings:
                curve_data = inverter.get(curve_key)
                if curve_data and isinstance(curve_data, list):
                    # Filter out any invalid data points
                    valid_points = []
                    for point in curve_data:
                        if isinstance(point, tuple) and len(point) == 2:
                            try:
                                dc_input = float(point[0])
                                ac_output = float(point[1])
                                valid_points.append((dc_input, ac_output))
                            except (ValueError, TypeError):
                                continue

                    if valid_points:
                        result_key = f"efficiency_at_{label}_voltage"
                        result[result_key] = valid_points

    return result
