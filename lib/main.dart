import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:hive_flutter/adapters.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import 'package:smartsecurity/controller/theme_bloc/theme_bloc.dart';
import 'package:smartsecurity/controller/theme_bloc/theme_state.dart';
import 'package:smartsecurity/services/shared_preferences_service.dart';
import 'package:smartsecurity/services/theme_service.dart';
import 'package:smartsecurity/view/splash/splash_screen.dart';
import 'package:toastification/toastification.dart';
import 'services/get_it.dart';
import 'common/const/firebase_options.dart';


void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter(); // Initialize Hive
  await Hive.openBox('Box'); // Open a Hive box
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  await SharedPreferencesService.instance.init();
  getItSetup();
  ThemeService.getTheme();
  runApp(MultiBlocProvider(
    providers: [
      BlocProvider(
        create: (context) => getIt<AppCubit>()..init(),
      ),
      BlocProvider(
        create: (context) => getIt<ThemeBloc>(),
      ),
    ],
    child: const MyApp(),
  ));
}

class MyApp extends StatefulWidget {
  const MyApp({super.key});

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {

  @override
  void initState() {
    ThemeService.initialize(context);
    super.initState();
  }

  @override
  Future<void> didChangeDependencies() async {
    ThemeService.autoChangeTheme(context);
    super.didChangeDependencies();
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<ThemeBloc, ThemeState>(
      builder: (context, state) {
        return ToastificationWrapper(
          child: MaterialApp(
            title: 'Security ID',
            debugShowCheckedModeBanner: false,
            theme: ThemeService.buildTheme(state),
            home: const SplashScreen(),
          ),
        );
      },
    );
  }
}
