import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/controller/theme_bloc/theme_state.dart';
import 'package:smartsecurity/services/shared_preferences_service.dart';
import '../controller/theme_bloc/theme_bloc.dart';
import '../controller/theme_bloc/theme_event.dart';


class ThemeService {
  static bool useDeviceTheme = true;
  static bool isDark = false;

  static Color darkBackground = const Color(0xFF211d52);
  static Color darkElement = const Color(0xFF110d3e);
  static Color darkSelections = const Color(0xFF7c7ff5);

  static Color lightBackground = const Color(0xFFe5e5e5);
  static Color lightElement = const Color(0xFFffffff);
  static Color lightSelections = const Color(0xFFffc676);

  static void initialize(BuildContext context) {
    ThemeBloc themeBloc = BlocProvider.of<ThemeBloc>(context);
    var brightness = SchedulerBinding.instance.platformDispatcher.platformBrightness;
    bool isDarkMode = ThemeService.isDark;
    if (ThemeService.useDeviceTheme) {
      isDarkMode = brightness == Brightness.dark;
    }
    themeBloc.add(ChangeTheme(useDeviceTheme: ThemeService.useDeviceTheme, isDark: isDarkMode));
  }

  // static setStatusBar(isDarkMode) {
  //   SystemChrome.setSystemUIOverlayStyle(  SystemUiOverlayStyle(
  //     statusBarBrightness: isDarkMode? Brightness.dark : Brightness.light,
  //     statusBarIconBrightness: isDarkMode? Brightness.light : Brightness.dark,
  //     systemNavigationBarDividerColor: isDarkMode? CupertinoColors.darkBackgroundGray : Colors.blue,
  //     systemNavigationBarIconBrightness: isDarkMode? Brightness.light : Brightness.dark,
  //     systemNavigationBarColor: isDarkMode? CupertinoColors.darkBackgroundGray : Colors.blue, // navigation bar color
  //     statusBarColor: isDarkMode?  CupertinoColors.darkBackgroundGray: Colors.blue , // status bar color
  //   ));
  // }

  static void autoChangeTheme(BuildContext context) async {
    ThemeBloc themeBloc = BlocProvider.of<ThemeBloc>(context);
    var brightness = MediaQuery.of(context).platformBrightness;
    ThemeService.getTheme();
    bool isDarkMode = ThemeService.isDark;
    if (ThemeService.useDeviceTheme) {
      isDarkMode = brightness == Brightness.dark;
    }
    themeBloc.add(ChangeTheme(useDeviceTheme: ThemeService.useDeviceTheme, isDark: isDarkMode));
  }

  static Future<void> setTheme({required bool useDeviceTheme, required bool isDark}) async {
    await SharedPreferencesService.instance.setData(PreferenceKey.useDeviceTheme, useDeviceTheme);
    await SharedPreferencesService.instance.setData(PreferenceKey.isDark, isDark);
  }

  static void getTheme() {
    useDeviceTheme = SharedPreferencesService.instance.getData(PreferenceKey.useDeviceTheme) ?? true;
    isDark = SharedPreferencesService.instance.getData(PreferenceKey.isDark) ?? false;
  }

  static ThemeData buildTheme(ThemeState state) {
    return ThemeData(
      brightness: state.isDark ? Brightness.dark : Brightness.light,
      primaryColor: CupertinoColors.systemIndigo,
      appBarTheme:  AppBarTheme(
        backgroundColor:  state.isDark ? darkBackground : lightBackground,
      ),
      cardTheme: CardTheme(
        color: state.isDark ? darkElement : lightElement,
        elevation: 0,
      ),
      drawerTheme: DrawerThemeData(
        backgroundColor: state.isDark ? darkBackground : lightBackground,
      ),

      scaffoldBackgroundColor: state.isDark ? darkBackground : lightBackground,

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: state.isDark ? darkSelections : lightSelections,
          foregroundColor: state.isDark ? darkElement : darkElement,
        ),
      )

    );
  }
}
