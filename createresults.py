"""
The file responsible for writing results into an excel to analyse the data

Bart van Nobelen - 05-07-2022
"""

import pandas as pd
import numpy as np

from domain.import_object import *
from modules.defaultmodule import DefaultModule
from util.repository import Repository
from domain.StrategicReserveOperator import StrategicReserveOperator
from util import globalNames

import logging
class CreatingResultsExcel(DefaultModule):

    def __init__(self, reps: Repository, operator: StrategicReserveOperator):
        super().__init__("Creating Results Excel", reps)
        reps.dbrw.stage_init_financial_results_structure()
        self.operator = operator
        if self.reps.current_tick == 0:
            self.ticks = []
            self.years = []
            self.marketclearingvolume = []      # MW
            self.marketclearingprice = []       # EUR
            self.total_installed_capacity = []
            self.nr_of_powerplants = []
            self.nr_of_powerplants_in_sr = []
            # self.cost_of_sr = []       # EUR
            # self.volume_of_sr = []      # MW

            self.average_electricity_price = []         # EUR/MWh
            self.shortage_hours = []        # hours/year
            self.supply_ratio = []      # MW/MW

            self.cost_to_consumer = []       # EUR/MWh
            self.CM_volume = []     # MW
            self.CM_price = []      # EUR
            self.CM_cost_per_MW = []       # EUR/MWh
            self.SR_operator_cash = []      # EUR
            self.SR_volume = []     # MW
            self.SR_price = []      # EUR
            self.SR_cost_per_MW = []       # EUR/MWh

            self.pp_name = []
            self.pp_owner = []
            self.pp_location = []
            self.pp_technology = []
            self.pp_fuel = []
            self.pp_age = []
            self.pp_efficiency = []
            self.pp_capacity = []
            self.pp_acceptedcapacity = []
            self.pp_status = []
            self.pp_profit = []
            self.pp_fixedoperatingcosts = []
            self.pp_variablecosts = []
            self.pp_revenues = []

    def act(self):
        self.ticks.append(self.reps.current_tick)
        self.years.append(self.reps.current_year)
        installed_capacity = 0
        for i in self.reps.power_plants.values():
            installed_capacity += i.capacity
        self.total_installed_capacity.append(installed_capacity)

        self.get_shortage_hours(self.reps.current_year, installed_capacity)

        self.nr_of_powerplants.append(len(self.reps.power_plants))
        self.nr_of_powerplants_in_sr.append(len(self.operator.list_of_plants))

        self.get_marketclearingpoint(self.reps.current_tick)
        self.get_power_plant_dispatch_plans(self.reps.current_tick)
        self.get_accepted_bids_CM(self.reps.current_tick)


        self.SR_operator_cash.append(self.operator.getCash())
        self.SR_volume.append(self.operator.getReserveVolume())
        # self.SR_price.append(self.operator.getCash())
        # self.SR_cost_per_MW = []       # EUR/MWh
        # self.cost_to_consumer_CM.append(0)
        # self.cost_to_consumer.append(0)

        overview = pd.DataFrame({'Year':self.years,
                                 'Market clearing volume':self.marketclearingvolume,
                                 'Market clearing price':self.marketclearingprice,
                                 'Average price of electricity':self.average_electricity_price,
                                 'Number of power plants':self.nr_of_powerplants,
                                 'Total installed capacity':self.total_installed_capacity,
                                 'Shortage hours':self.shortage_hours,
                                 'Supply ratio':self.supply_ratio,
                                 'CM volume':self.CM_volume,
                                 'CM price':self.CM_price,
                                 'CM price per MW':self.CM_cost_per_MW,
                                 'Number of power plants in SR':self.nr_of_powerplants_in_sr,
                                 'SR volume':self.SR_volume,
                                 'SR operator cash':self.SR_operator_cash,
                                 })

        powerplant_data = pd.DataFrame()

        for powerplant in self.reps.power_plants.values():
            self.pp_name = powerplant.name
            self.pp_owner = powerplant.owner.name
            self.pp_location = powerplant.location
            self.pp_technology = powerplant.technology.name
            if powerplant.technology.fuel != '':
                self.pp_fuel = powerplant.technology.fuel.name
            else:
                self.pp_fuel = ''
            self.pp_age = powerplant.age
            self.pp_efficiency = powerplant.actualEfficiency
            self.pp_capacity = powerplant.actualNominalCapacity
            self.pp_acceptedcapacity = powerplant.AwardedPowerinMWh
            self.pp_status = powerplant.status
            self.pp_profit = powerplant.Profit
            self.pp_fixedoperatingcosts = powerplant.actualFixedOperatingCost
            self.pp_variablecosts = powerplant.technology.variable_operating_costs
            self.pp_revenues = self.reps.get_power_plant_electricity_spot_market_revenues_by_tick(powerplant.id, self.reps.current_tick)
            powerplant_values = pd.DataFrame({'Name':self.pp_name,
                                              'Owner':self.pp_owner,
                                              'Technology':self.pp_technology,
                                              'Fuel':self.pp_fuel,
                                              'Age':self.pp_age,
                                              'Efficiency':self.pp_efficiency,
                                              'Capacity':self.pp_capacity,
                                              'Accepted capacity':self.pp_acceptedcapacity,
                                              'Status':self.pp_status,
                                              'Profit':self.pp_profit,
                                              'Fixed Operating Costs':self.pp_fixedoperatingcosts,
                                              'Variable Costs':self.pp_variablecosts,
                                              'Revenues':self.pp_revenues}, index=[0])
            powerplant_data = pd.concat([powerplant_data, powerplant_values], ignore_index=True)
            # powerplant_data.append(powerplant_values, ignore_index=True)

        writer = pd.ExcelWriter('Yearly_results.xlsx')
        overview.to_excel(writer, sheet_name='Overview')
        pp_year = 'Powerplants' + str(self.reps.current_year)
        powerplant_data.to_excel(writer, sheet_name=pp_year)
        writer.save()


    def get_marketclearingpoint(self, tick):
        total_volume = 0
        total_price = 0
        for i in self.reps.market_clearing_points.values():
            if i.time == tick and i.market.name == 'GermanCapacityMarket':
                total_volume += i.volume
                total_price += i.price
        self.marketclearingvolume.append(total_volume)
        self.marketclearingprice.append(total_price)

    def get_accepted_bids_CM(self, tick):
        accepted_amount = 0
        total_price = 0
        for i in self.reps.bids.values():
            if i.tick == tick and i.market == 'GermanCapacityMarket' and \
                    (i.status == globalNames.power_plant_dispatch_plan_status_partly_accepted or
                     i.status == globalNames.power_plant_dispatch_plan_status_accepted):
                accepted_amount += i.accepted_amount
                total_price += i.price
        self.CM_volume.append(accepted_amount)
        self.CM_price.append(total_price)
        if total_price == 0 or accepted_amount == 0:
            price_per_mw = 0
        else:
            price_per_mw = total_price/accepted_amount
        self.CM_cost_per_MW.append(price_per_mw)

    def get_shortage_hours(self, year, capacity):
        demand_list = []
        trend = self.reps.dbrw.get_calculated_simulated_fuel_prices_by_year("electricity", globalNames.simulated_prices, year)
        peak_load_without_trend = max(self.reps.get_hourly_demand_by_power_grid_node_and_year('DE')[1])
        peak_load_volume = peak_load_without_trend * trend
        count = 0
        for i in self.reps.electricity_spot_markets.values():
            if i.name == 'GermanElectricitySpotMarket':
                demand_list = i.hourlyDemand[1].values
        for i in demand_list:
            x = i * trend
            if x > capacity:
                count += 1
        self.shortage_hours.append(count)
        self.supply_ratio.append(capacity/peak_load_volume)

    def get_power_plant_dispatch_plans(self, tick):
        count = 0
        sum = 0
        for i in self.reps.power_plant_dispatch_plans.values():
            if i.tick == tick:
                count += 1
                sum += i.price
        if count == 0 or sum == 0:
            average_price = 0
        else:
            average_price = sum/count
        self.average_electricity_price.append(average_price)
        # if len(self.reps.power_plant_dispatch_plans) != 0:
        #     count = 0
        #     sum = 0
        #     for i in self.reps.power_plant_dispatch_plans.values():
        #         if i.tick == tick:
        #             count += 1
        #             sum += i.price
        #     self.average_electricity_price.append(sum/count)
        # else:
        #     self.average_electricity_price.append(0)







    # key = self.reps.current_tick - 1
    # MarketClearingPoints = []
    # for i in self.reps.market_clearing_points.values():
    #     MarketClearingPoints.append(i)
    # if MarketClearingPoints == []:
    #     self.marketclearingvolume.append(0)
    #     self.marketclearingprice.append(0)
    # else:
    #     temp_marketclearingpoint = MarketClearingPoints[key]
    #     self.marketclearingvolume.append(temp_marketclearingpoint.volume)
    #     self.marketclearingprice.append(temp_marketclearingpoint.price)
    # # return MarketClearingPoints[key]

