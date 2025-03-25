import 'package:get_it/get_it.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';

import '../controller/theme_bloc/theme_bloc.dart';
import '../model/permissions.dart';
import 'firebase_auth.dart';
import 'firebase_real_time.dart';

final getIt = GetIt.I;

void getItSetup() {

  // bloc
  getIt.registerSingleton<AppCubit>(AppCubit());
  getIt.registerSingleton<ThemeBloc>(ThemeBloc());

  // firebase real time
  getIt.registerSingleton<FirebaseRealTimeDB>(FirebaseRealTimeDB());
  // firebase auth
  getIt.registerSingleton<FirebaseAuthRepo>(FirebaseAuthRepo());

  getIt.registerSingleton<PermissionsRepo>(PermissionsRepo());



}
