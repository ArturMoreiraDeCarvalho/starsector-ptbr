package data.hullmods;

import java.util.HashMap;
import java.util.Map;

import com.fs.starfarer.api.combat.BaseHullMod;
import com.fs.starfarer.api.combat.MutableShipStatsAPI;
import com.fs.starfarer.api.combat.ShipAPI;
import com.fs.starfarer.api.combat.ShipAPI.HullSize;
import com.fs.starfarer.api.impl.campaign.ids.HullMods;

public class DedicatedTargetingCore extends BaseHullMod {

	public static Map mag = new HashMap();
	static {
		mag.put(HullSize.FIGHTER, 0f);
		mag.put(HullSize.FRIGATE, 0f);
		mag.put(HullSize.DESTROYER, 0f);
		mag.put(HullSize.CRUISER, 35f);
		mag.put(HullSize.CAPITAL_SHIP, 50f);
	}
	
	public String getDescriptionParam(int index, HullSize hullSize) {
		if (index == 0) return "" + ((Float) mag.get(HullSize.CRUISER)).intValue() + "%";
		if (index == 1) return "" + ((Float) mag.get(HullSize.CAPITAL_SHIP)).intValue() + "%";
		return null;
	}
	
	public String getSModDescriptionParam(int index, HullSize hullSize) {
		if (index == 0) return "" + ((Float) IntegratedTargetingUnit.mag.get(HullSize.CRUISER)).intValue() + "%";
		if (index == 1) return "" + ((Float) IntegratedTargetingUnit.mag.get(HullSize.CAPITAL_SHIP)).intValue() + "%";
		return null;
	}
	
	public void applyEffectsBeforeShipCreation(HullSize hullSize, MutableShipStatsAPI stats, String id) {
		boolean sMod = isSMod(stats);
		Map map = mag;
		if (sMod) map = IntegratedTargetingUnit.mag;
		stats.getBallisticWeaponRangeBonus().modifyPercent(id, (Float) map.get(hullSize));
		stats.getEnergyWeaponRangeBonus().modifyPercent(id, (Float) map.get(hullSize));
	}

	@Override
	public boolean isApplicableToShip(ShipAPI ship) {
		return (ship.getHullSize() == HullSize.CAPITAL_SHIP || ship.getHullSize() == HullSize.CRUISER) &&
				!ship.getVariant().getHullMods().contains("targetingunit") &&
				!ship.getVariant().getHullMods().contains(HullMods.DISTRIBUTED_FIRE_CONTROL) &&
				!ship.getVariant().getHullMods().contains("advancedcore");
	}
	
	
	public String getUnapplicableReason(ShipAPI ship) {
		if (ship != null && ship.getHullSize() != HullSize.CAPITAL_SHIP && ship.getHullSize() != HullSize.CRUISER) {
			return "Só pode ser instalado em cruzadores e naves capitais";
		}
		if (ship.getVariant().getHullMods().contains("targetingunit")) {
			return "Incompatível com Unidade de Mira Integrada";
		}
		if (ship.getVariant().getHullMods().contains("advancedcore")) {
			return "Incompatível com Núcleo de Mira Avançado";
		}
		if (ship.getVariant().getHullMods().contains(HullMods.DISTRIBUTED_FIRE_CONTROL)) {
			return "Incompatível com Controle de Fogo Distribuído";
		}
		
		return null;
	}
	
}
