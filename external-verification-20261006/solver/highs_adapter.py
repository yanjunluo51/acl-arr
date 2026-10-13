"""Same SciPy MILP arrays, sent to the already-installed highspy 1.15.1.

No model change, no proprietary solver, no paid service. The result message
records the backend version so receipts cannot be confused with SciPy's backend.
"""
from types import SimpleNamespace
import numpy as np
import highspy

def milp(c,integrality,bounds,constraints,options):
 h=highspy.Highs();version=h.version()
 for k,v in dict(output_flag=False,threads=1,random_seed=0,mip_rel_gap=0.,time_limit=float(options['time_limit']),presolve='on' if options.get('presolve',True) else 'off').items():
  assert h.setOptionValue(k,v)==highspy.HighsStatus.kOk,(k,v)
 A=constraints.A.tocsc();lp=highspy.HighsLp()
 lp.num_col_=len(c);lp.num_row_=A.shape[0]
 lp.col_cost_=np.asarray(c,dtype=float);lp.col_lower_=np.asarray(bounds.lb,dtype=float);lp.col_upper_=np.asarray(bounds.ub,dtype=float)
 lp.row_lower_=np.asarray(constraints.lb,dtype=float);lp.row_upper_=np.asarray(constraints.ub,dtype=float)
 assert set(np.unique(integrality))<={0,1}
 lp.integrality_=[highspy.HighsVarType.kInteger if i else highspy.HighsVarType.kContinuous for i in integrality]
 lp.a_matrix_.format_=highspy.MatrixFormat.kColwise
 lp.a_matrix_.start_=A.indptr;lp.a_matrix_.index_=A.indices;lp.a_matrix_.value_=A.data
 assert h.passModel(lp)==highspy.HighsStatus.kOk
 h.run();s=h.getModelStatus();info=h.getInfo();sol=h.getSolution()
 status={highspy.HighsModelStatus.kOptimal:0,highspy.HighsModelStatus.kTimeLimit:1,highspy.HighsModelStatus.kIterationLimit:1,highspy.HighsModelStatus.kInfeasible:2,highspy.HighsModelStatus.kUnbounded:3}.get(s,4)
 feasible=sol.value_valid and info.primal_solution_status==highspy.SolutionStatus.kSolutionStatusFeasible
 return SimpleNamespace(status=status,message='highspy '+version+': '+h.modelStatusToString(s),x=np.asarray(sol.col_value) if feasible else None,
  fun=float(info.objective_function_value) if feasible else None,mip_dual_bound=float(info.mip_dual_bound),mip_gap=float(info.mip_gap))
